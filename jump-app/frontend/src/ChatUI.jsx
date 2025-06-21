import React, { useState, useEffect, useRef } from 'react';
import { User, Bot, Send, Sparkles } from 'lucide-react';
import.meta.env.VITE_API_BASE_URL;

const ChatMessage = ({ msg }) => {
  const Icon = {
    user: User,
    bot: Bot,
  }[msg.sender] || Bot;

  const bgColor = {
    user: 'bg-blue-600 text-white',
    bot: 'bg-gray-100 dark:bg-gray-700',
  }[msg.sender];

  return (
    <div className={`flex items-start gap-3 my-4 ${msg.sender === 'user' ? 'justify-end' : ''}`}>
      {msg.sender !== 'user' && (
        <Icon className="w-7 h-7 p-1.5 rounded-full bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300 flex-shrink-0" />
      )}
      <div className={`max-w-xl p-3 rounded-xl ${bgColor} ${msg.sender === 'user' ? 'rounded-br-none' : 'rounded-bl-none'}`}>
        <p className="text-sm">{msg.text}</p>
      </div>
      {msg.sender === 'user' && (
        <User className="w-7 h-7 p-1.5 rounded-full bg-blue-600 text-white flex-shrink-0" />
      )}
    </div>
  );
};

export default function ChatUI() {
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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-100 via-gray-50 to-indigo-100 dark:from-gray-900 dark:via-gray-800 dark:to-indigo-950 font-sans">
      <div className="flex flex-col w-full max-w-2xl min-h-[70vh] bg-white dark:bg-gray-900 shadow-2xl rounded-2xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        {/* Header */}
        <header className="flex items-center gap-3 p-5 border-b border-gray-200 dark:border-gray-800 bg-indigo-50 dark:bg-gray-800">
          <Sparkles className="text-indigo-500 w-7 h-7" />
          <h2 className="font-semibold text-lg tracking-tight text-gray-900 dark:text-gray-100">AI Chat Agent</h2>
        </header>
  
        {/* Messages */}
        <div className="flex-1 px-6 py-6 overflow-y-auto bg-gradient-to-br from-white via-indigo-50 to-gray-100 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
          {messages.map((msg, i) => (
            <ChatMessage key={i} msg={msg} />
          ))}
          {isLoading && (
            <div className="flex items-center gap-3 my-4">
              <Bot className="w-6 h-6 animate-pulse" />
              <div>Loading...</div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
  
        {/* Input */}
        <div className="p-5 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
          <form onSubmit={handleSubmit} className="flex items-center gap-4">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question or give a command..."
              className="flex-1 p-3 bg-gray-100 dark:bg-gray-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading}
              className="p-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-indigo-300 disabled:cursor-not-allowed transition-all"
              aria-label="Send"
            >
              <Send />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
