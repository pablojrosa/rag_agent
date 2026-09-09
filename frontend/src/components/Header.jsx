import React from 'react';
import { NavLink } from 'react-router-dom';
import './Header.css';

const Header = () => {
  return (
    <header className="app-header">
      <div className="header-branding">
        <h1>Scanntech Chatbot</h1>
        <h2>Chat with: "An Introduction to Statistical Learning"</h2>
      </div>

      <nav className="header-nav">
        <NavLink to="/" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          Chat
        </NavLink>
      </nav>
    </header>
  );
};

export default Header;
