"""Flask API for chat persistence and Langfuse dashboards."""
import os
import uuid
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_migrate import Migrate

from src.app.models import db, ChatMessage, Conversation
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
    # ingest data request
    data = request.get_json(silent=True)

    # validations
    if not isinstance(data, dict):
        return jsonify(error="A JSON object is required."), 400
    message, session_id = data.get("message"), data.get("session_id")
    history = data.get("history_chat", [])
    if not isinstance(message, str) or not message.strip() or not isinstance(session_id, str) or not session_id:
        return jsonify(error="message and session_id are required strings."), 400
    if not isinstance(history, list) or not all(isinstance(item, dict) for item in history):
        return jsonify(error="history_chat must be a list of messages."), 400

    # process request
    message_id = str(uuid.uuid4())
    try:
        # trace request
        with session_attributes(session_id), observation(
            "chat-request", input={"question": message},
            metadata={"message_id": message_id, "mode": "online"}
        ) as span:
            # answer question
            answer_payload = answer_question(message, history, structured=True)
            if isinstance(answer_payload, str):
                answer_payload = {"answer": answer_payload, "charts": []}
            answer = answer_payload["answer"]
            # save conversation
            with observation("save-conversation"):
                conversation = db.session.get(Conversation, session_id)
                if conversation is None:
                    conversation = Conversation(session_id=session_id,
                                                title=message.strip()[:200])
                    db.session.add(conversation)
                elif conversation.deleted:
                    conversation.deleted = False
                conversation.updated_at = datetime.utcnow()
                db.session.add(ChatMessage(session_id=session_id, sender="user", message=message))
                db.session.add(ChatMessage(message_id=message_id, session_id=session_id,
                                           sender="agent", message=answer))
                db.session.commit()
            # update span
            span.update(output=answer)
            return jsonify(response=answer, artifacts=answer_payload.get("charts", []),
                           message_id=message_id, trace_id=span.trace_id)
    except Exception:
        # rollback conversation
        db.session.rollback()
        # log error
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


@app.get("/conversations")
def conversations():
    items = (Conversation.query.filter_by(deleted=False)
             .order_by(Conversation.updated_at.desc()).all())
    return jsonify(conversations=[{
        "session_id": item.session_id,
        "title": item.title,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    } for item in items])


@app.get("/conversations/<session_id>/messages")
def conversation_messages(session_id):
    conversation = db.session.get(Conversation, session_id)
    if conversation is None or conversation.deleted:
        return jsonify(error="Conversation not found."), 404
    messages = (ChatMessage.query.filter_by(session_id=session_id)
                .order_by(ChatMessage.timestamp.asc()).all())
    return jsonify(messages=[{
        "message_id": item.message_id,
        "sender": item.sender,
        "message": item.message,
        "timestamp": item.timestamp.isoformat(),
    } for item in messages])


@app.patch("/conversations/<session_id>/delete")
def delete_conversation(session_id):
    conversation = db.session.get(Conversation, session_id)
    if conversation is None:
        return jsonify(error="Conversation not found."), 404
    conversation.deleted = True
    conversation.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(deleted=True, session_id=session_id)


@app.get("/conversation-metrics")
def conversation_metrics():
    return dashboard("online")


@app.get("/offline-evaluation-results")
def offline_results():
    return dashboard("offline")


if __name__ == "__main__":
    app.run(debug=True, port=5001)
