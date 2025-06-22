import React, { useState, useEffect, useRef } from 'react';
import { User, Bot, Send, Sparkles, LogOut } from 'lucide-react';
import.meta.env.VITE_API_BASE_URL;

// Enhanced markdown renderer with better styling
const MarkdownRenderer = ({ content }) => {
  const renderMarkdown = (text) => {
    const lines = text.split('\n');
    
    return lines.map((line, index) => {
      if (line.startsWith('## ')) {
        return (
          <h2 key={index} className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-3 mt-6">
            {line.replace('## ', '')}
          </h2>
        );
      }
      
      if (line.startsWith('### ')) {
        return (
          <h3 key={index} className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-2 mt-4">
            {line.replace('### ', '')}
          </h3>
        );
      }
      
      if (line.includes('**')) {
        const parts = line.split('**');
        return (
          <p key={index} className="mb-3 text-gray-700 dark:text-gray-300">
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
      
      if (line.trim().startsWith('- ')) {
        return (
          <ul key={index} className="list-disc ml-5 mb-3 space-y-1">
            <li className="text-gray-700 dark:text-gray-300">
              {line.replace('- ', '')}
            </li>
          </ul>
        );
      }
      
      if (/^\d+\.\s/.test(line)) {
        return (
          <ol key={index} className="list-decimal ml-5 mb-3 space-y-1">
            <li className="text-gray-700 dark:text-gray-300">
              {line.replace(/^\d+\.\s/, '')}
            </li>
          </ol>
        );
      }
      
      if (line.trim()) {
        return <p key={index} className="mb-3 text-gray-700 dark:text-gray-300">{line}</p>;
      }
      
      return <div key={index} className="h-3"></div>;
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
    user: 'bg-gradient-to-r from-blue-500 to-blue-600 text-white',
    bot: 'bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700',
  }[msg.sender];

  const textColor = {
    user: 'text-white',
    bot: 'text-gray-800 dark:text-gray-200',
  }[msg.sender];

  return (
    <div className={`flex items-start gap-3 my-4 ${msg.sender === 'user' ? 'justify-end' : ''}`}>
      {msg.sender !== 'user' && (
        <div className="flex-shrink-0">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-md">
            <Icon className="w-5 h-5 text-white" />
          </div>
        </div>
      )}
      <div className={`max-w-xl p-5 rounded-3xl ${bgColor} ${msg.sender === 'user' ? 'rounded-br-none' : 'rounded-bl-none'} shadow-sm hover:shadow-md transition-shadow duration-200`}>
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
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center shadow-md">
            <User className="w-5 h-5 text-white" />
          </div>
        </div>
      )}
    </div>
  );
};

export default function ChatUI({ onLogout }) {
  const [messages, setMessages] = useState([
    { sender: 'bot', text: "Hello! I'm your AI Financial Advisor Agent. How can I help you today?\n\nYou can ask me about:\n- Investment strategies\n- Budget planning\n- Retirement savings\n- Tax optimization" }
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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 via-blue-50 to-indigo-100 dark:from-gray-900 dark:via-gray-800 dark:to-gray-950 font-sans">
      <div className="flex flex-col w-full max-w-4xl min-h-[90vh] bg-white dark:bg-gray-900 shadow-xl rounded-xl border border-gray-100 dark:border-gray-800 overflow-hidden transition-all duration-300">
        {/* Header */}
        <header className="flex items-center justify-between p-5 border-b border-gray-100 dark:border-gray-800 bg-gradient-to-r from-indigo-600 to-purple-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center backdrop-blur-sm">
              <Sparkles className="text-white w-5 h-5" />
            </div>
            <div>
              <h2 className="font-bold text-xl text-white">AI Financial Advisor</h2>
              <p className="text-indigo-100 text-sm">Your personal financial assistant</p>
            </div>
          </div>
          <button
            onClick={onLogout}
            className="p-2.5 bg-white/10 text-white rounded-lg hover:bg-white/20 transition-all duration-200 backdrop-blur-sm flex items-center gap-2"
            aria-label="Logout"
          >
            <LogOut className="w-4 h-4" />
            <span className="text-sm font-medium hidden sm:inline">Logout</span>
          </button>
        </header>
  
        {/* Messages */}
        <div className="flex-1 px-5 py-5 overflow-y-auto bg-gradient-to-b from-white to-gray-50 dark:from-gray-900 dark:to-gray-800/50">
          {messages.map((msg, i) => (
            <ChatMessage key={i} msg={msg} />
          ))}
          {isLoading && (
            <div className="flex items-center gap-3 my-4">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center animate-pulse">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div className="flex space-x-2">
                <div className="w-3 h-3 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-3 h-3 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-3 h-3 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
  
        {/* Input */}
        <div className="p-5 border-t border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900/80 backdrop-blur-sm">
          <form onSubmit={handleSubmit} className="flex items-center gap-3">
            <div className="flex-1 relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about investments, savings, or financial planning..."
                className="w-full p-4 pr-14 bg-gray-50 dark:bg-gray-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white dark:focus:bg-gray-700 transition-all duration-200 shadow-sm hover:shadow-md"
                disabled={isLoading}
              />
              {isLoading && (
                <div className="absolute right-4 top-1/2 transform -translate-y-1/2 flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                </div>
              )}
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="p-4 bg-gradient-to-r from-indigo-600 to-purple-700 text-white rounded-xl hover:from-indigo-700 hover:to-purple-800 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed transition-all duration-200 shadow-lg hover:shadow-xl active:scale-95"
              aria-label="Send message"
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 text-center">
            AI may produce inaccurate information. Verify important details.
          </p>
        </div>
      </div>
    </div>
  );
}