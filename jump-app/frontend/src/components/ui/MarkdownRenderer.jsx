// src/components/MarkdownRenderer.jsx
import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

const MarkdownRenderer = ({ content }) => {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderContent = (text) => {
    const parts = text.split('```');
    const elements = [];

    parts.forEach((part, index) => {
      if (index % 2 === 1) { // It's a code block
        elements.push(
          <div key={`code-block-${index}`} className="my-4 relative rounded-xl overflow-hidden">
            <div className="bg-black/40 backdrop-blur-sm text-green-400 font-mono text-sm p-4 overflow-x-auto custom-scrollbar border border-white/10">
              <div className="flex justify-between items-center mb-2 -mt-2 -mx-2 bg-black/60 backdrop-blur-sm px-3 py-2 rounded-t-lg sticky top-0 z-10 border-b border-white/10">
                <span className="text-white/60 text-xs font-medium">Code Snippet</span>
                <button
                  onClick={() => copyToClipboard(part.trim())}
                  className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white/80 hover:text-white transition-all duration-200 flex items-center justify-center border border-white/20"
                  aria-label={copied ? "Copied" : "Copy code"}
                >
                  {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
              <pre className="whitespace-pre-wrap text-sm">{part}</pre>
            </div>
          </div>
        );
      } else { // It's regular text content
        elements.push(<React.Fragment key={`text-block-${index}`}>{renderTextContent(part)}</React.Fragment>);
      }
    });

    return elements;
  };

  const renderTextContent = (text) => {
    const lines = text.split('\n');
    const elements = [];
    let inList = false;
    let listType = null;

    lines.forEach((line, index) => {
      if (line.trim().startsWith('- ') || /^\d+\.\s/.test(line.trim())) {
        if (!inList) {
          inList = true;
          listType = line.trim().startsWith('- ') ? 'ul' : 'ol';
          elements.push(React.createElement(listType, { key: `list-start-${index}`, className: "mb-4 ml-6 space-y-2" }));
        }
        elements.push(
          <li key={`list-item-${index}`} className="text-white/90 leading-relaxed">
            {line.replace(/^(- |\d+\.\s)/, '').trim()}
          </li>
        );
      } else {
        if (inList) {
          elements.push(React.createElement(listType, { key: `list-end-${index}` }));
          inList = false;
          listType = null;
        }
        if (line.startsWith('### ')) {
          elements.push(
            <h3 key={`h3-${index}`} className="text-lg font-bold text-white mb-3 mt-6 first:mt-0">
              {line.replace('### ', '')}
            </h3>
          );
        } else if (line.startsWith('## ')) {
          elements.push(
            <h2 key={`h2-${index}`} className="text-xl font-bold text-white mb-4 mt-6 first:mt-0">
              {line.replace('## ', '')}
            </h2>
          );
        } else if (line.startsWith('# ')) {
          elements.push(
            <h1 key={`h1-${index}`} className="text-2xl font-bold text-white mb-5 mt-6 first:mt-0">
              {line.replace('# ', '')}
            </h1>
          );
        } else if (line.trim()) {
          // Handle bold, italic, and links within paragraphs
          let processedLine = line;
          processedLine = processedLine.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>');
          processedLine = processedLine.replace(/\*(.*?)\*/g, '<em class="text-white/80 italic">$1</em>');
          const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
          processedLine = processedLine.replace(linkRegex, '<a href="$2" class="text-blue-400 hover:text-blue-300 underline transition-colors duration-200" target="_blank" rel="noopener noreferrer">$1</a>');

          elements.push(
            <p key={`text-${index}`} className="mb-4 leading-relaxed text-white/90"
               dangerouslySetInnerHTML={{ __html: processedLine }} />
          );
        } else {
          // Empty lines for spacing
          elements.push(<div key={`empty-${index}`} className="h-4"></div>);
        }
      }
    });

    if (inList) { // Close any open list at the end
      elements.push(React.createElement(listType, { key: `list-end-final` }));
    }

    return elements;
  };

  return (
    <div className="prose prose-invert max-w-none">
      {renderContent(content)}
    </div>
  );
};

export default MarkdownRenderer;