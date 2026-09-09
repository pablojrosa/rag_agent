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
    return { text: data.response, artifacts: data.artifacts || [] };

  } catch (error) {
    console.error('Connection error:', error);
    return 'Oops! I could not connect to the server. Make sure it is running.';
  }
};

export async function getConversations() {
  const response = await fetch(`${API_URL}/conversations`);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Could not load conversations.');
  return data.conversations;
}

export async function getConversationMessages(sessionId) {
  const response = await fetch(`${API_URL}/conversations/${sessionId}/messages`);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Could not load conversation.');
  return data.messages;
}

export async function deleteConversation(sessionId) {
  const response = await fetch(`${API_URL}/conversations/${sessionId}/delete`, { method: 'PATCH' });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Could not delete conversation.');
  return data;
}

export async function getEvaluationDashboard(mode, params, signal) {
  const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value !== '' && value != null));
  const path = mode === 'offline' ? '/offline-evaluation-results' : '/conversation-metrics';
  const response = await fetch(`${API_URL}${path}?${query}`, { signal });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Could not load evaluations.');
  return data;
}
