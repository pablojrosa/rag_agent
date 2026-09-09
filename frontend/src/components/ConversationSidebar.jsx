import { useEffect, useState } from 'react';
import { deleteConversation, getConversationMessages, getConversations } from '../api/chatService';
import './ConversationSidebar.css';

function ConversationSidebar({ activeSessionId, onSelect, onNew, refreshKey }) {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    getConversations().then(items => {
      if (mounted) setConversations(items);
    }).catch(error => console.error(error)).finally(() => mounted && setLoading(false));
    return () => { mounted = false; };
  }, [refreshKey]);

  const handleSelect = async (conversation) => {
    try {
      const messages = await getConversationMessages(conversation.session_id);
      onSelect(conversation, messages);
    } catch (error) {
      console.error(error);
    }
  };

  const handleDelete = async (event, conversation) => {
    event.stopPropagation();
    if (!window.confirm('Hide this conversation from your history?')) return;
    try {
      await deleteConversation(conversation.session_id);
      setConversations(items => items.filter(item => item.session_id !== conversation.session_id));
      if (activeSessionId === conversation.session_id) onNew();
    } catch (error) {
      console.error(error);
    }
  };

  return <aside className="conversation-sidebar">
    <div className="sidebar-heading"><div><span className="sidebar-kicker">Workspace</span><h2>Conversations</h2></div><span className="conversation-count">{conversations.length}</span></div>
    <button className="new-conversation" onClick={onNew}><span>+</span> New conversation</button>
    <div className="conversation-list">
      {loading && <p className="sidebar-empty">Loading history...</p>}
      {!loading && !conversations.length && <p className="sidebar-empty">Your saved conversations will appear here.</p>}
      {conversations.map(item => <button className={`conversation-item ${activeSessionId === item.session_id ? 'active' : ''}`} key={item.session_id} onClick={() => handleSelect(item)}>
        <span className="conversation-item-main"><strong>{item.title}</strong><small>{new Date(item.updated_at).toLocaleDateString()}</small></span>
        <span className="delete-conversation" role="button" tabIndex="0" aria-label={`Hide ${item.title}`} onClick={event => handleDelete(event, item)}>×</span>
      </button>)}
    </div>
  </aside>;
}

export default ConversationSidebar;
