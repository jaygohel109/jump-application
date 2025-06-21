import React, { useState, useEffect, useRef } from 'react';
import { User, Bot, Send, Sparkles, LogOut } from 'lucide-react';
import.meta.env.VITE_API_BASE_URL;

// Simple markdown renderer component
const MarkdownRenderer = ({ content }) => {
  const renderMarkdown = (text) => {
    // Split by lines to handle different markdown elements
    const lines = text.split('\n');
    
    return lines.map((line, index) => {
      // Handle headers (## Title)
      if (line.startsWith('## ')) {
        return (
          <h2 key={index} className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-2 mt-4">
            {line.replace('## ', '')}
          </h2>
        );
      }
      
      // Handle bold text (**text**)
      if (line.includes('**')) {
        const parts = line.split('**');
        return (
          <p key={index} className="mb-2">
            {parts.map((part, partIndex) => 
              partIndex % 2 === 1 ? (
                <strong key={partIndex} className="font-semibold">{part}</strong>
              ) : (
                part
              )
            )}
          </p>
        );
      }
      
      // Handle bullet points
      if (line.trim().startsWith('- ')) {
        return (
          <li key={index} className="ml-4 mb-1">
            {line.replace('- ', '')}
          </li>
        );
      }
      
      // Handle numbered lists
      if (/^\d+\.\s/.test(line)) {
        return (
          <li key={index} className="ml-4 mb-1">
            {line.replace(/^\d+\.\s/, '')}
          </li>
        );
      }
      
      // Regular text
      if (line.trim()) {
        return <p key={index} className="mb-2">{line}</p>;
      }
      
      // Empty lines
      return <div key={index} className="h-2"></div>;
    });
  };

  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      {renderMarkdown(content)}
    </div>
  );
};

const ChatMessage = ({ msg }) => {
  const Icon = {
    user: User,
    bot: Bot,
  }[msg.sender] || Bot;

  const bgColor = {
    user: 'bg-blue-600 text-white',
    bot: 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700',
  }[msg.sender];

  const textColor = {
    user: 'text-white',
    bot: 'text-gray-900 dark:text-gray-100',
  }[msg.sender];

  return (
    <div className={`flex items-start gap-3 my-4 ${msg.sender === 'user' ? 'justify-end' : ''}`}>
      {msg.sender !== 'user' && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <Icon className="w-5 h-5 text-white" />
          </div>
        </div>
      )}
      <div className={`max-w-xl p-4 rounded-2xl shadow-sm ${bgColor} ${msg.sender === 'user' ? 'rounded-br-md' : 'rounded-bl-md'}`}>
        {msg.sender === 'user' ? (
          <p className={`text-sm ${textColor}`}>{msg.text}</p>
        ) : (
          <div className={textColor}>
            <MarkdownRenderer content={msg.text} />
          </div>
        )}
      </div>
      {msg.sender === 'user' && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
            <User className="w-5 h-5 text-white" />
          </div>
        </div>
      )}
    </div>
  );
};

export default function ChatUI({ onLogout }) {
  const [messages, setMessages] = useState([
    { sender: 'bot', text: "Hello! I'm your AI Financial Advisor Agent. How can I help you today?" }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const addMessage = (sender, text) => {
    setMessages((prev) => [...prev, { sender, text }]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = input;
    addMessage('user', userMessage);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question: userMessage })
      });

      const data = await response.json();
      addMessage('bot', data.answer || 'No response from backend.');
    } catch (err) {
      console.error(err);
      addMessage('bot', 'There was an error talking to the backend.');
    }

    setIsLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 via-blue-50 to-indigo-100 dark:from-gray-900 dark:via-gray-800 dark:to-indigo-950 font-sans">
      <div className="flex flex-col w-full max-w-4xl min-h-[80vh] bg-white dark:bg-gray-900 shadow-2xl rounded-2xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        {/* Header */}
        <header className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800 bg-gradient-to-r from-indigo-500 to-purple-600">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
              <Sparkles className="text-white w-6 h-6" />
            </div>
            <div>
              <h2 className="font-bold text-xl text-white">AI Financial Advisor</h2>
              <p className="text-indigo-100 text-sm">Your personal financial assistant</p>
            </div>
          </div>
          <button
            onClick={onLogout}
            className="p-3 bg-white/20 text-white rounded-xl hover:bg-white/30 transition-all duration-200 backdrop-blur-sm"
            aria-label="Logout"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </header>
  
        {/* Messages */}
        <div className="flex-1 px-6 py-6 overflow-y-auto bg-gradient-to-br from-gray-50 to-white dark:from-gray-900 dark:to-gray-800">
          {messages.map((msg, i) => (
            <ChatMessage key={i} msg={msg} />
          ))}
          {isLoading && (
            <div className="flex items-center gap-3 my-4">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center animate-pulse">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
  
        {/* Input */}
        <div className="p-6 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
          <form onSubmit={handleSubmit} className="flex items-center gap-4">
            <div className="flex-1 relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about your finances, emails, or anything else..."
                className="w-full p-4 pr-12 bg-gray-100 dark:bg-gray-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white dark:focus:bg-gray-700 transition-all duration-200"
                disabled={isLoading}
              />
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="p-4 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl hover:from-indigo-600 hover:to-purple-700 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed transition-all duration-200 shadow-lg hover:shadow-xl"
              aria-label="Send"
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
