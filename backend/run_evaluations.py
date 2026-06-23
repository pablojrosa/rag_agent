import os
import pandas as pd
import uuid
from dotenv import load_dotenv
from sqlalchemy import create_engine
from datasets import Dataset
from ragas.evaluation import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
    answer_correctness
)
from ragas.run_config import RunConfig 
from datetime import datetime
from src.app.main_agent import main_agent
from src.app.rag_tool import semantic_search_raw

PROMPT_TEMPLATE = """
You are an expert assistant on the book "An Introduction to Statistical Learning with Applications in Python".
Your task is to answer the user's question based ONLY and EXCLUSIVELY on the following context.
Do not invent information or use external knowledge. If the answer is not in the context, say so.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
"""

def run_offline_evaluation():
    """
    Run a full RAG system evaluation using the golden_dataset stored in
    the PostgreSQL database.
    """

    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_timestamp = datetime.utcnow()

    load_dotenv()
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    if not db_url:
        raise ValueError("DATABASE_URL not found. Make sure your .env file is configured.")

    print("🔌 Connecting to the database...")
    engine = create_engine(db_url)
    
    query = "SELECT id, question, ground_truth FROM golden_dataset LIMIT 5"
    df = pd.read_sql_query(query, engine)
    print(f"✅ Loaded {len(df)} questions from the golden_dataset table.")
    results = []
    print("🚀 Running the RAG system for each question (this may take a while)...")
    
    chat_session = main_agent.start_chat(enable_automatic_function_calling=False)

    for index, row in df.iterrows():
        question = row['question']
        
        search_result = semantic_search_raw(question)
        context = search_result['context']
    
        final_prompt = PROMPT_TEMPLATE.format(context=context, question=question)
        
    
        response = chat_session.send_message(final_prompt)
        answer = response.text 
        
        results.append({
            "question": question,
            "ground_truth": row['ground_truth'],
            "answer": answer,
            "contexts": [context]
        })
    
    rag_results_df = pd.DataFrame(results)

    rag_results_df['ground_truths'] = rag_results_df['ground_truth'].apply(lambda x: [x]) 
    evaluation_dataset = Dataset.from_pandas(rag_results_df)

    run_config = RunConfig(max_workers=1)

    print("📊 Starting the full evaluation with Ragas...")
    result = evaluate(
        evaluation_dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall, answer_correctness],
        run_config=run_config
    )

    result_df = result.to_pandas()
    result_df['answer'] = rag_results_df['answer']
    result_df['golden_dataset_id'] = df['id'] 
    result_df['run_id'] = run_id
    result_df['run_timestamp'] = run_timestamp
    

    columns_to_save = {
        'golden_dataset_id': 'golden_dataset_id',
        'run_id': 'run_id',
        'run_timestamp': 'run_timestamp',
        'answer': 'generated_answer', 
        'faithfulness': 'faithfulness',
        'answer_relevancy': 'answer_relevancy',
        'context_precision': 'context_precision',
        'context_recall': 'context_recall',
        'answer_correctness': 'answer_correctness'
    }
    
    final_df = result_df[list(columns_to_save.keys())].rename(columns=columns_to_save)

    try:
        final_df.to_sql(
            'evaluation_results',
            con=engine,
            if_exists='append',
            index=False
        )
        return result_df
    except Exception as e:
        print(f"❌ Error saving results to the database: {e}")


if __name__ == '__main__':
    run_offline_evaluation()
