import React, { useState, useEffect, useRef } from 'react';
import { User, Bot, Send, Sparkles, LogOut } from 'lucide-react';
import ChatMessage from './components/ui/ChatMessage';

export default function ChatUI({ userInfo, onLogout, onSessionExpired }) {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState({
    google: userInfo?.hasGoogle || false,
    hubspot: userInfo?.hasHubspot || false
  });
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Add welcome message
    setMessages([
      {
        id: 1,
        type: 'assistant',
        content: `Welcome! I'm your AI assistant. I can help you with:\n\n- 📧 **Email Management**: Search and analyze your emails\n- 👥 **Contact Management**: Access HubSpot contacts and notes\n- 📅 **Calendar Management**: View and create calendar events\n- 📝 **Note Taking**: Create notes in HubSpot\n\nWhat would you like to do today?`,
        timestamp: new Date().toISOString()
      }
    ]);
  }, []);

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/chat/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          message: inputMessage
        })
      });

      if (response.status === 401) {
        onSessionExpired();
        return;
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      const assistantMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Update connection status if provided in response
      if (data.context) {
        setConnectionStatus({
          google: data.context.has_google,
          hubspot: data.context.has_hubspot
        });
      }

    } catch (error) {
      console.error('Error sending message:', error);
      
      const errorMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: 'Sorry, I encountered an error while processing your request. Please try again.',
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleBulkImport = async () => {
    setIsLoading(true);
    
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/chat/bulk-import`, {
        method: 'POST',
        credentials: 'include'
      });

      if (response.status === 401) {
        onSessionExpired();
        return;
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      const importMessage = {
        id: Date.now(),
        type: 'assistant',
        content: `✅ Bulk import completed!\n\n**Results:**\n- Emails: ${data.results.emails?.success || 0} imported\n- HubSpot contacts: ${data.results.hubspot_data?.success || 0} imported\n- Calendar events: ${data.results.calendar_events?.success || 0} imported\n\nYou can now ask me about your data!`,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, importMessage]);

    } catch (error) {
      console.error('Error during bulk import:', error);
      
      const errorMessage = {
        id: Date.now(),
        type: 'assistant',
        content: 'Sorry, I encountered an error during the bulk import. Please try again.',
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-semibold text-gray-900">Jump Agent</h1>
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${connectionStatus.google ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className="text-sm text-gray-600">Google</span>
              <div className={`w-2 h-2 rounded-full ${connectionStatus.hubspot ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className="text-sm text-gray-600">HubSpot</span>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <button
              onClick={handleBulkImport}
              disabled={isLoading}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {isLoading ? 'Importing...' : 'Import Data'}
            </button>
            <div className="text-sm text-gray-600">
              {userInfo?.email}
            </div>
            <button
              onClick={onLogout}
              className="px-4 py-2 text-sm bg-gray-600 text-white rounded-md hover:bg-gray-700"
            >
              Logout
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
        
        {isLoading && (
          <div className="flex items-center space-x-2 text-gray-500">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            <span>Thinking...</span>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-white border-t px-6 py-4">
        <div className="flex space-x-4">
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message here..."
            className="flex-1 resize-none border border-gray-300 rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            rows="1"
            disabled={isLoading}
          />
          <button
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isLoading}
            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
