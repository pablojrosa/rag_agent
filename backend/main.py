from flask import Flask, request, jsonify, current_app
from flask_cors import CORS
from src.app.main_agent import main_agent
from src.app.rag_tool import semantic_search_raw
import os 
from flask_migrate import Migrate
from src.app.models import db, ChatMessage, ConversationEval, EvaluationResult, GoldenDataset
import threading
import numpy as np
from src.app.evaluation_worker import run_online_evaluation

app = Flask(__name__)
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

CORS(app, resources={r"/*": {"origins": allowed_origins}}, supports_credentials=True)


db_url = os.environ.get('DATABASE_URL')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message')
    session_id = data.get('session_id')
    history = data.get('history_chat', [])

    if not message or not session_id:
        return jsonify({'error': 'Missing required fields: "message" or "session_id"'}), 400

    try:
        # save user message
        user_message = ChatMessage(session_id=session_id, sender='user', message=message)
        db.session.add(user_message)

        search_result = semantic_search_raw(message)
        context = search_result["context"]
        scores = search_result["scores"]
        avg_confidence = np.mean(scores) if scores else 0.0
    
        chat_session = main_agent.start_chat(history=history, enable_automatic_function_calling=True)

        response = chat_session.send_message(message)
        text_response = response.text
        # save agent message
        agent_message = ChatMessage(session_id=session_id, sender='agent', message=text_response)
        db.session.add(agent_message)
        db.session.commit()

        agent_message_id = agent_message.message_id
        eval_thread = threading.Thread(
            target=run_online_evaluation,
            args=(
                current_app._get_current_object(),
                message,
                text_response,
                context,
                session_id,
                agent_message_id
            )
        )
        eval_thread.start()

        return jsonify({
            'response': text_response
        })
    
    except Exception as e:
        db.session.rollback()
        print((f"❌ Error processing message: {str(e)}"))
        return jsonify({'error': f'Error processing message: {str(e)}'}), 500

@app.route('/offline-evaluation-results', methods=['GET'])
def get_offline_evaluation_results():
    """
    Endpoint to retrieve the results from the latest offline evaluation run.
    """
    try:

        latest_run = db.session.query(EvaluationResult.run_id).order_by(EvaluationResult.run_timestamp.desc()).first()
        if not latest_run:
            return jsonify([])

        latest_run_id = latest_run[0]

        query = db.session.query(EvaluationResult, GoldenDataset).join(
            GoldenDataset, EvaluationResult.golden_dataset_id == GoldenDataset.id
        ).filter(EvaluationResult.run_id == latest_run_id).all()
        
        results_list = []
        for eval_result, golden_entry in query:
            results_list.append({
                'question': golden_entry.question,
                'generated_answer': eval_result.generated_answer,
                'faithfulness': eval_result.faithfulness,
                'answer_relevancy': eval_result.answer_relevancy,
                'context_precision': eval_result.context_precision,
                'context_recall': eval_result.context_recall,
                'answer_correctness': eval_result.answer_correctness
            })
            
        return jsonify(results_list)

    except Exception as e:
        print(f"❌ Error fetching offline evaluation results: {str(e)}")
        return jsonify({'error': f'Error fetching results: {str(e)}'}), 500

@app.route('/conversation-metrics', methods=['GET'])
def get_conversation_metrics():
    try:
        query = db.session.query(ConversationEval, ChatMessage).join(
            ChatMessage, ConversationEval.message_id == ChatMessage.message_id
        ).order_by(ConversationEval.timestamp.desc()).limit(100)  # Fetch the latest 100
        
        results = query.all()
        
        metrics_list = []
        for eval_result, chat_message in results:
            metrics_list.append({
                'message_id': eval_result.message_id,
                'user_question': eval_result.user_question,
                'message_text': chat_message.message,
                'faithfulness': eval_result.faithfulness,
                'answer_relevancy': eval_result.answer_relevancy,
                'session_id': eval_result.session_id,
                'timestamp': eval_result.timestamp.isoformat(),
            })
            
        return jsonify(metrics_list)

    except Exception as e:
        print(f"❌ Error fetching conversation metrics: {str(e)}")
        return jsonify({'error': f'Error fetching metrics: {str(e)}'}), 500
    
if __name__ == '__main__':
    app.run(debug=True, port=5001)
