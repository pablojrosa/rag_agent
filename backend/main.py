"""Flask API for chat persistence and Langfuse dashboards."""
import os
import uuid

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_migrate import Migrate

from src.app.models import db, ChatMessage
from src.app.observability import observation, session_attributes
from src.app.rag_service import answer_question
from src.app.monitoring import monitoring_payload, MonitoringUnavailable

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:5173").split(",")}}, supports_credentials=True)
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL is required. Configure backend/.env.")
app.config["SQLALCHEMY_DATABASE_URI"] = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
migrate = Migrate(app, db)


@app.post("/chat")
def chat():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="A JSON object is required."), 400
    message, session_id = data.get("message"), data.get("session_id")
    history = data.get("history_chat", [])
    if not isinstance(message, str) or not message.strip() or not isinstance(session_id, str) or not session_id:
        return jsonify(error="message and session_id are required strings."), 400
    if not isinstance(history, list) or not all(isinstance(item, dict) for item in history):
        return jsonify(error="history_chat must be a list of messages."), 400
    message_id = str(uuid.uuid4())
    try:
        with session_attributes(session_id), observation(
            "chat-request", input={"question": message},
            metadata={"message_id": message_id, "mode": "online"}
        ) as span:
            answer = answer_question(message, history)
            with observation("save-conversation"):
                db.session.add(ChatMessage(session_id=session_id, sender="user", message=message))
                db.session.add(ChatMessage(message_id=message_id, session_id=session_id,
                                           sender="agent", message=answer))
                db.session.commit()
            span.update(output=answer)
            return jsonify(response=answer, message_id=message_id, trace_id=span.trace_id)
    except Exception:
        db.session.rollback()
        app.logger.exception("Chat request failed")
        return jsonify(error="Could not process the message. Check the backend logs."), 500


def dashboard(kind):
    try:
        days = int(request.args.get("days", 7))
        if not 1 <= days <= 90:
            raise ValueError()
        return jsonify(monitoring_payload(kind, days=days,
                       cursor=request.args.get("cursor"), experiment_id=request.args.get("experiment_id")))
    except ValueError:
        return jsonify(error="days must be between 1 and 90."), 400
    except MonitoringUnavailable:
        return jsonify(error="Langfuse is unavailable. Check its configuration and try again."), 503


@app.get("/conversation-metrics")
def conversation_metrics():
    return dashboard("online")


@app.get("/offline-evaluation-results")
def offline_results():
    return dashboard("offline")


if __name__ == "__main__":
    app.run(debug=True, port=5001)
