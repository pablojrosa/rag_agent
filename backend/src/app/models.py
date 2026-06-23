from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref

db = SQLAlchemy()

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    message_id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String, nullable=False, index=True)
    sender = db.Column(db.String(10), nullable=False)  # 'user' or 'agent'
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    message = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<ChatMessage {self.sender}@{self.session_id}: {self.message[:30]}>"
    
class ConversationEval(db.Model):
    __tablename__ = 'conversation_evals'

    eval_id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = db.Column(db.String, ForeignKey('chat_messages.message_id'), nullable=False, unique=True)
    user_question = db.Column(db.Text, nullable=False)
    session_id = db.Column(db.String, nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    faithfulness = db.Column(db.Float, nullable=True)
    answer_relevancy = db.Column(db.Float, nullable=True)
    chat_message = relationship(
        "ChatMessage",
        backref=backref("evaluation", uselist=False, cascade="all, delete-orphan")
    )

    def __repr__(self):
        return f"<ConversationEval for message {self.message_id}>"
    

class GoldenDataset(db.Model):
    __tablename__ = 'golden_dataset'

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False, unique=True)
    ground_truth = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<GoldenDataset Question: {self.question[:50]}>"
    
class EvaluationResult(db.Model):
    __tablename__ = 'evaluation_results'

    id = db.Column(db.Integer, primary_key=True)
    
    golden_dataset_id = db.Column(db.Integer, db.ForeignKey('golden_dataset.id'), nullable=False)
    generated_answer = db.Column(db.Text, nullable=True)
    run_id = db.Column(db.String, nullable=False, index=True)
    run_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    faithfulness = db.Column(db.Float, nullable=True)
    answer_relevancy = db.Column(db.Float, nullable=True)
    context_precision = db.Column(db.Float, nullable=True)
    context_recall = db.Column(db.Float, nullable=True)
    answer_correctness = db.Column(db.Float, nullable=True)
    golden_dataset_entry = relationship("GoldenDataset", backref="evaluation_results")

    def __repr__(self):
        return f"<EvaluationResult for run {self.run_id} on question {self.golden_dataset_id}>"
