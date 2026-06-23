import { useState } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { sendMessageToBot } from '../api/chatService';
import ChatWindow from './ChatWindow';
import InputBar from './InputBar';
import './ChatPage.css'; 
import '../App.css';
const formatTime = (date) => {
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  return `${hours}:${minutes}:${seconds}`;
};

const getSessionId = () => {
  let sessionId = localStorage.getItem('chatSessionId');
  if (!sessionId) {
    sessionId = uuidv4();
    localStorage.setItem('chatSessionId', sessionId);
  }
  return sessionId;
};

function ChatPage() {
  const [messages, setMessages] = useState([
    { sender: 'bot', 
      text: 'Welcome to the chat for "An Introduction to Statistical Learning with Applications in Python." How can I help you today?',
      timestamp: formatTime(new Date()) }
  ]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async (inputText) => {
    if (!inputText.trim()) return;

    const userMessage = { 
      sender: 'user',
      text: inputText,
      timestamp: formatTime(new Date()) 
     };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setIsLoading(true);
    
  
    const sessionId = getSessionId();
    
    try {
      const botReplyText = await sendMessageToBot(
        inputText,          
        updatedMessages,    
        sessionId           
      ); 
      
      const botMessage = { 
        sender: 'bot',
        text: botReplyText,
        timestamp: formatTime(new Date())
      };
      setMessages(prev => [...prev, botMessage]);

    } catch (error) {
      console.error('Error in handleSendMessage:', error);
      const errorMessage = {
        sender: 'bot',
        text: 'Oops! Something went wrong while connecting to the bot.',
        timestamp: formatTime(new Date())
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <ChatWindow messages={messages} />
      {isLoading && <div className="loading-indicator">The bot is thinking...</div>}
      <InputBar onSendMessage={handleSendMessage} disabled={isLoading} />
    </div>
  );
}

export default ChatPage;
