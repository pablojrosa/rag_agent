import { Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import ChatPage from './components/ChatPage';

import './App.css';

function App() {
  return (
    <div className="app-container">
      <Header /> 
      <main className="main-content">
        <Routes>
          <Route path="/" element={<ChatPage />} />
        </Routes>
      </main>
    </div>
  );
}
export default App;
