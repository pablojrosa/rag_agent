import React, { useState } from 'react';
import './InputBar.css';

const InputBar = ({ onSendMessage, disabled }) => {
  const [inputText, setInputText] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputText.trim() && !disabled) {
      onSendMessage(inputText);
      setInputText('');
    }
  };

  return (
    <form className="input-bar-container" onSubmit={handleSubmit}>
      <input
        type="text"
        className="input-field"
        placeholder="Type your message..."
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        disabled={disabled}
      />
      <button type="submit" className="send-button" disabled={disabled}>
        Send
      </button>
    </form>
  );
};

export default InputBar;
