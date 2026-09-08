"""Optional Langfuse telemetry that never masks application failures."""
import atexit
import logging
import os
from contextlib import contextmanager
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def configured():
    return (os.getenv("LANGFUSE_ENABLED", "true").lower() == "true"
            and bool(os.getenv("LANGFUSE_PUBLIC_KEY"))
            and bool(os.getenv("LANGFUSE_SECRET_KEY")))


@lru_cache(maxsize=1)
def get_client():
    if not configured():
        return None
    from langfuse import Langfuse
    return Langfuse(timeout=5, environment=os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "development"))


class Observation:
    def __init__(self, span=None):
        self.span = span

    def update(self, **kwargs):
        if self.span is not None:
            try:
                self.span.update(**kwargs)
            except Exception:
                logger.warning("Could not update telemetry")

    @property
    def trace_id(self):
        return getattr(self.span, "trace_id", None)


@contextmanager
def observation(name, **kwargs):
    manager = None
    span = None
    try:
        client = get_client()
        if client:
            manager = client.start_as_current_observation(name=name, **kwargs)
            span = manager.__enter__()
    except Exception:
        manager = None
        logger.warning("Could not start telemetry")
    handle = Observation(span)
    try:
        yield handle
    except BaseException as exc:
        handle.update(level="ERROR", status_message=type(exc).__name__)
        raise
    finally:
        if manager:
            try:
                manager.__exit__(None, None, None)
            except Exception:
                logger.warning("Could not finish telemetry")


@contextmanager
def session_attributes(session_id):
    manager = None
    try:
        if configured():
            from langfuse import propagate_attributes
            manager = propagate_attributes(session_id=session_id)
            manager.__enter__()
    except Exception:
        manager = None
        logger.warning("Could not set telemetry session")
    try:
        yield
    finally:
        if manager:
            try:
                manager.__exit__(None, None, None)
            except Exception:
                logger.warning("Could not finish telemetry session")


def flush():
    if get_client.cache_info().currsize:
        try:
            client = get_client()
            if client:
                client.flush()
        except Exception:
            logger.warning("Could not flush telemetry")


atexit.register(flush)
