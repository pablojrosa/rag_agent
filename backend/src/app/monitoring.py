"""Read Langfuse definitions and results without exposing service credentials."""
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from .observability import get_client

logger = logging.getLogger(__name__)
PAGE_SIZE = 20


class MonitoringUnavailable(Exception):
    pass


def record(value):
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else value


def field(item, snake_name, camel_name=None):
    return item.get(snake_name) if snake_name in item else item.get(camel_name or snake_name)


def trace_url(trace_id):
    project = os.getenv("LANGFUSE_PROJECT_ID")
    if not project or not trace_id:
        return None
    base = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com").rstrip("/")
    return f"{base}/project/{quote(project, safe='')}/traces/{quote(trace_id, safe='')}"


def metric_key(score):
    return field(score, "config_id", "configId") or f"{score['name']}:{field(score, 'data_type', 'dataType')}"


def definitions(client):
    result = []
    page = 1
    selected = {name.strip() for name in os.getenv("DASHBOARD_SCORE_NAMES", "").split(",") if name.strip()}
    while True:
        response = record(client.api.score_configs.get(page=page, limit=100))
        for item in response["data"]:
            if field(item, "is_archived", "isArchived") or (selected and item["name"] not in selected):
                continue
            result.append({"key": item["id"], "name": item["name"],
                           "label": item["name"].replace("_", " ").capitalize(),
                           "type": field(item, "data_type", "dataType"),
                           "description": item.get("description"),
                           "min": field(item, "min_value", "minValue"),
                           "max": field(item, "max_value", "maxValue")})
        if page >= response.get("meta", {}).get("total_pages", 1):
            return result
        page += 1


def scores_for(client, *, observation_id=None, trace_id=None):
    result, cursor = [], None
    while True:
        response = record(client.api.scores_v3.get_many_v3(
            observation_id=observation_id, trace_id=trace_id, limit=100, cursor=cursor))
        result.extend(response["data"])
        cursor = response["meta"].get("cursor")
        if not cursor:
            return result


def scores_map(scores, catalog):
    allowed = {item["name"] for item in catalog}
    mapped = {}
    for score in sorted(scores, key=lambda item: item.get("timestamp", "")):
        if score["name"] not in allowed:
            continue
        key = metric_key(score)
        if not score.get("config_id"):
            matching = [item for item in catalog if item["name"] == score["name"] and
                        item["type"] == field(score, "data_type", "dataType")]
            if len(matching) == 1:
                key = matching[0]["key"]
        # Scores without a config still retain their name and type as a stable key.
        if not any(item["key"] == key for item in catalog):
            catalog.append({"key": key, "name": score["name"], "label": score["name"],
                            "type": field(score, "data_type", "dataType"), "description": None})
        mapped[key] = {"value": score.get("value"), "comment": score.get("comment")}
    return mapped


def decode_output(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def performance_summary(client, start):
    query = {
        "view": "observations", "dimensions": [{"field": "name"}],
        "metrics": [{"measure": "count", "aggregation": "count"},
                    {"measure": "latency", "aggregation": "avg"},
                    {"measure": "totalTokens", "aggregation": "sum"},
                    {"measure": "totalCost", "aggregation": "sum"}],
        "filters": [{"type": "string", "column": "traceName", "operator": "=", "value": "chat-request"},
                    {"type": "string", "column": "environment", "operator": "=",
                     "value": os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "development")}],
        "fromTimestamp": start.isoformat(), "toTimestamp": datetime.now(timezone.utc).isoformat(),
    }
    return record(client.api.metrics.metrics(query=json.dumps(query)))["data"]


def monitoring_payload(kind, days=7, cursor=None, experiment_id=None):
    try:
        client = get_client()
        if client is None:
            return {"configured": False, "metrics": [], "rows": [], "runs": [], "next_cursor": None}
        catalog = definitions(client)
        start = datetime.now(timezone.utc) - timedelta(days=days)
        runs = []
        if kind == "online":
            response = record(client.api.observations.get_many(
                name="rag-answer", from_start_time=start, limit=PAGE_SIZE, cursor=cursor,
                environment=os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "development"),
                fields="core,basic,io,metadata",
                filter=json.dumps([
                    {"type": "string", "column": "name", "operator": "=", "value": "rag-answer"},
                    {"type": "datetime", "column": "startTime", "operator": ">=", "value": start.isoformat()},
                    {"type": "string", "column": "environment", "operator": "=",
                     "value": os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "development")},
                    {"type": "stringObject", "column": "metadata", "key": "mode",
                                    "operator": "=", "value": "online"}])))
            items = response["data"]
            batch = scores_for(client, trace_id=",".join(field(item, "trace_id", "traceId") for item in items),
                               observation_id=",".join(item["id"] for item in items)) if items else []
            all_scores = [[score for score in batch if score.get("observation_id") == item["id"]
                           and field(score, "trace_id", "traceId") == field(item, "trace_id", "traceId")] for item in items]
        else:
            dataset = client.api.datasets.get(os.getenv("LANGFUSE_DATASET_NAME", "statistical-learning"))
            run_response = record(client.api.experiments.list(
                from_start_time=start, dataset_id=dataset.id, limit=50))
            runs = [{"id": item["id"], "name": item["name"],
                     "timestamp": field(item, "start_time", "startTime"),
                     "metadata": item.get("metadata")} for item in run_response["data"]]
            selected = experiment_id or (runs[0]["id"] if runs else None)
            if not selected:
                return {"configured": True, "metrics": catalog, "rows": [], "runs": [], "next_cursor": None}
            response = record(client.api.experiments.list_items(
                from_start_time=start, dataset_id=dataset.id, experiment_id=selected,
                fields="core,io,metadata", limit=PAGE_SIZE, cursor=cursor))
            items = response["data"]
            batch = scores_for(client, trace_id=",".join(field(item, "trace_id", "traceId") for item in items)) if items else []
            all_scores = [[score for score in batch if field(score, "trace_id", "traceId") == field(item, "trace_id", "traceId")]
                          for item in items]
        rows = []
        for item, scores in zip(items, all_scores):
            data = item.get("input") or {}
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except ValueError:
                    data = {"question": data}
            if not isinstance(data, dict):
                data = {"question": str(data)}
            start_time, end_time = field(item, "start_time", "startTime"), field(item, "end_time", "endTime")
            latency = None
            if start_time and end_time:
                latency = (datetime.fromisoformat(end_time.replace("Z", "+00:00")) -
                           datetime.fromisoformat(start_time.replace("Z", "+00:00"))).total_seconds()
            mapped = scores_map(scores, catalog)
            rows.append({"id": item["id"], "question": data.get("question", ""),
                         "answer": decode_output(item.get("output")),
                         "expected_output": field(item, "expected_output", "expectedOutput"),
                         "session_id": field(item, "session_id", "sessionId"), "timestamp": start_time,
                         "latency_seconds": latency, "scores": mapped,
                         "status": "error" if item.get("level") == "ERROR" else
                                   ("evaluated" if mapped else "unscored"),
                         "trace_url": trace_url(field(item, "trace_id", "traceId"))})
        return {"configured": True, "metrics": catalog, "rows": rows, "runs": runs,
                "experiment_id": selected if kind == "offline" else None,
                "performance": performance_summary(client, start) if kind == "online" else [],
                "next_cursor": response["meta"].get("cursor")}
    except Exception as exc:
        logger.warning("Langfuse dashboard request failed (%s)", type(exc).__name__)
        raise MonitoringUnavailable() from exc
