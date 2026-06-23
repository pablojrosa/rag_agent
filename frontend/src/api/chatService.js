const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

function formatHistoryForBackend(messages) {
  const conversationHistory = messages.slice(1);
  
  return conversationHistory.map(msg => ({
    role: msg.sender === 'user' ? 'user' : 'model',
    parts: [{ text: msg.text }]
  }));
}

export const sendMessageToBot = async (inputText, currentMessages, sessionId) => {
  const historyForBackend = formatHistoryForBackend(currentMessages);

  const payload = {
    message: inputText,
    history_chat: historyForBackend,
    session_id: sessionId
  };

  try {
    const response = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error('Server error:', errorData);
      return 'Oops! Something went wrong while connecting to the bot.';
    }

    const data = await response.json();
    return data.response;

  } catch (error) {
    console.error('Connection error:', error);
    return 'Oops! I could not connect to the server. Make sure it is running.';
  }
};

export const getOfflineEvaluationResults = async () => {
  try {
    const response = await fetch(`${API_URL}/offline-evaluation-results`);
    if (!response.ok) throw new Error('Server error.');
    return await response.json();
  } catch (error) {
    console.error('Error fetching evaluation results:', error);
    throw error;
  }
};

export const getConversationMetrics = async () => {
  try {
    const response = await fetch(`${API_URL}/conversation-metrics`);
    if (!response.ok) throw new Error('Server error while fetching metrics.');
    return await response.json();
  } catch (error) {
    console.error('Error fetching conversation metrics:', error);
    throw error;
  }
};
