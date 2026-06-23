import React, { useState, useEffect } from 'react';
import { getOfflineEvaluationResults } from '../api/chatService';
import './TableStyles.css';

function OfflineEvalsPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const data = await getOfflineEvaluationResults();
        setResults(data);
      } catch (err) {
        setError('Could not load results. Run an evaluation from your terminal.');
      }
      setIsLoading(false);
    };
    fetchResults();
  }, []);

  if (isLoading) return <p>Loading the latest evaluation results...</p>;
  if (error) return <p className="error-message">{error}</p>;

  return (
    <div className="page-container">
      <h2>Latest Offline Evaluation Results</h2>
      <p>
        These are the scores from the latest evaluation run with <code>python run_evaluations.py</code>.
      </p>
      <div className="metrics-description">
        <h4>What does each metric mean?</h4>
        <dl>
          <dt><strong>Faithfulness:</strong></dt>
          <dd>
            Measures whether the generated answer is based ONLY on the provided context. A high score (close to 1) means the model is not hallucinating or inventing information.
          </dd>

          <dt><strong>Answer Relevancy:</strong></dt>
          <dd>
            Evaluates whether the answer is relevant and directly addresses the user's question. A low score may indicate that the answer is vague or off-topic.
          </dd>

          <dt><strong>Context Precision:</strong></dt>
          <dd>
            Focuses on the retrieval step. It measures how relevant the retrieved context is for answering the question. A high score indicates that little useless noise was retrieved.
          </dd>

          <dt><strong>Context Recall:</strong></dt>
          <dd>
            Also evaluates retrieval. It measures whether ALL the necessary information was recovered from the source text to answer the question completely. A low score suggests important parts were missed.
          </dd>

          <dt><strong>Answer Correctness:</strong></dt>
          <dd>
            Compares the generated answer with an ideal answer (ground truth). It measures accuracy and completeness. It is the most comprehensive quality metric, but it requires an evaluation dataset.
          </dd>
        </dl>
      </div>
      
      {results.length > 0 ? (
        <div className="table-container">
          <h3>Evaluation Results</h3>
          <table className="results-table">
            <thead>
              <tr>
                <th>Question</th>
                <th>Generated Answer</th>
                <th>Faithfulness</th>
                <th>Answer Relevancy</th>
                <th>Context Precision</th>
                <th>Context Recall</th>
                <th>Answer Correctness</th>
              </tr>
            </thead>
            <tbody>
              {results.map((item, index) => (
                <tr key={index}>
                  <td>{item.question}</td>
                  <td>{item.generated_answer}</td> 
                  <td>{item.faithfulness?.toFixed(2)}</td>
                  <td>{item.answer_relevancy?.toFixed(2)}</td>
                  <td>{item.context_precision?.toFixed(2)}</td>
                  <td>{item.context_recall?.toFixed(2)}</td>
                  <td>{item.answer_correctness?.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ):(<p>No results were found. Have you run an evaluation yet?</p>
      )}
    </div>
  );
}

export default OfflineEvalsPage;
