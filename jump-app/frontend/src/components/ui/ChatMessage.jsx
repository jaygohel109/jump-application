// src/components/ChatMessage.jsx
import React, { useState } from 'react';
import { User, Bot, Copy, Check, RotateCcw } from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer'; // Import the new MarkdownRenderer

const ChatMessage = ({ message }) => {
  const [copied, setCopied] = useState(false);

  // Map the new message format to the old format for compatibility
  const msg = {
    sender: message.type === 'user' ? 'user' : 'bot',
    text: message.content
  };

  const Icon = {
    user: User,
    bot: Bot,
  }[msg.sender] || Bot;

  const copyMessageToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`group animate-in fade-in-0 slide-in-from-bottom-2 duration-500 ${msg.sender === 'user' ? 'justify-end' : ''}`}>
      <div className={`flex items-start gap-4 max-w-4xl mx-auto ${msg.sender === 'user' ? 'flex-row-reverse' : ''}`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 ${msg.sender === 'user' ? 'order-2' : ''}`}>
          <div className={`w-10 h-10 rounded-full flex items-center justify-center shadow-md ${
            msg.sender === 'user'
              ? 'bg-gradient-to-br from-blue-500 to-blue-600'
              : 'bg-gradient-to-br from-purple-500 to-indigo-600'
          }`}>
            <Icon className="w-5 h-5 text-white" />
          </div>
        </div>

        {/* Message Bubble */}
        <div className={`flex-1 ${msg.sender === 'user' ? 'order-1' : ''}`}>
          <div className={`relative group/message ${
            msg.sender === 'user'
              ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-lg'
              : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-lg'
          } rounded-2xl p-4 sm:p-6 max-w-3xl ring-1 ring-gray-100 dark:ring-gray-700/50`}>

            {/* Message content */}
            {msg.sender === 'user' ? (
              <p className="text-white leading-relaxed text-base sm:text-lg">{msg.text}</p>
            ) : (
              <div className="text-gray-900 dark:text-gray-100">
                <MarkdownRenderer content={msg.text} />
              </div>
            )}

            {/* Message actions (hover) */}
            <div className="absolute top-2 right-2 opacity-0 group-hover/message:opacity-100 transition-opacity duration-200 flex gap-1">
              <button
                onClick={() => copyMessageToClipboard(msg.text)}
                className="p-1.5 rounded-lg bg-black/10 text-white hover:bg-black/20 transition-colors duration-200"
                aria-label={copied ? "Copied" : "Copy message"}
              >
                {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              </button>
              {msg.sender === 'bot' && (
                <button
                  className="p-1.5 rounded-lg bg-black/10 text-white hover:bg-black/20 transition-colors duration-200"
                  aria-label="Regenerate response"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>

          {/* Timestamp */}
          <div className={`text-xs text-gray-500 dark:text-gray-400 mt-2 ${msg.sender === 'user' ? 'text-right' : 'text-left'}`}>
            {message.timestamp ? new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;