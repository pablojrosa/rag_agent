import React, { useEffect, useRef } from 'react';
import Message from './Message';
import './ChatWindow.css';

const ChatWindow = ({ messages }) => {
  const messagesEndRef = useRef(null);
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div className="chat-window">
      {messages.map((msg, index) => (
        <Message 
          key={index} 
          sender={msg.sender} 
          text={msg.text} 
          artifacts={msg.artifacts}
          timestamp={msg.timestamp}
        />
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatWindow;
