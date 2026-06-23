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
        <NavLink to="/offline-evals" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          Offline Monitoring
        </NavLink>
        <NavLink to="/conversation-metrics" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          Online Metrics
        </NavLink>
      </nav>
    </header>
  );
};

export default Header;
