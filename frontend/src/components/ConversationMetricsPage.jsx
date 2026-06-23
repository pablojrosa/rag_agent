import React, { useState, useEffect } from 'react';
import { getConversationMetrics } from '../api/chatService';
import './TableStyles.css';

function ConversationMetricsPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [metrics, setMetrics] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const data = await getConversationMetrics();
        setMetrics(data);
      } catch (err) {
        setError('Could not load metrics.');
      }
      setIsLoading(false);
    };
    fetchMetrics();
  }, []);

  if (isLoading) return <p>Loading metrics...</p>;
  if (error) return <p className="error-message">{error}</p>;

  return (
    <div className="page-container">
      <h2>Live Conversation Metrics (Latest 100)</h2>
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
        </dl>
      </div>
      <div className="table-container">
        <table className="results-table">
          <thead>
            <tr>
              <th>User Message</th>
              <th>Bot Message</th>
              <th>Faithfulness</th>
              <th>Answer Relevancy</th>
              <th>Session ID</th>
              <th>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((item) => (
              <tr key={item.message_id}>
                <td>{item.user_question}</td> 
                <td>{item.message_text}</td>
                <td>{item.faithfulness?.toFixed(2)}</td>
                <td>{item.answer_relevancy?.toFixed(2)}</td>
                <td>{item.session_id}</td>
                <td>{new Date(item.timestamp).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default ConversationMetricsPage;
