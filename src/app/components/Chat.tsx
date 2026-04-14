"use client";

import { useChat } from "@ai-sdk/react";
import { TextStreamChatTransport } from "ai";
import { useRef, useEffect, useState, useCallback } from "react";

export function Chat() {
  const [input, setInput] = useState("");

  const { messages, sendMessage, stop, status, error, setMessages } = useChat({
    transport: new TextStreamChatTransport({
      api: "/api/chat",
    }),
  });

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const isStreaming = status === "streaming" || status === "submitted";

  // Auto-scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-focus textarea
  useEffect(() => {
    if (!isStreaming && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isStreaming]);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!input.trim()) return;

      sendMessage({ text: input });
      setInput("");
    },
    [input, sendMessage],
  );

  const clearChat = () => {
    setMessages([]);
    setInput("");
  };

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Chat</h2>
        {messages.length > 0 && (
          <button
            onClick={clearChat}
            className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
            type="button"
          >
            Clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <svg className="w-12 h-12 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-label="Chat icon">
              <title>Chat</title>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p className="text-sm">Start a conversation</p>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[80%] rounded-lg px-4 py-2 ${message.role === "user" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-900"}`}>
                  <p className="whitespace-pre-wrap text-sm">
                    {message.parts?.map((part, i) =>
                      part.type === "text" ? <span key={i}>{part.text}</span> : null
                    )}
                  </p>

                  {/*<p className="whitespace-pre-wrap text-sm">
                       {message.parts?.map((part, i) =>
                         part.type === "text" ? (
                           <span key={i}>
                             {i === 0 ? (part.text || "").replace(/^\n/, "") : part.text}
                           </span>
                         ) : null
                       )}
                     </p>*/}

                </div>
              </div>
            ))}
          </>
        )}

        {error && (
          <div className="flex justify-center">
            <div className="max-w-[80%] rounded-lg px-4 py-2 bg-red-100 text-red-900">
              <p className="text-sm">{error.message}</p>
            </div>
          </div>
        )}

        {isStreaming && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-4 py-2">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4">
        <form onSubmit={handleSubmit} className="flex gap-2 items-end">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            placeholder="Type message... (Shift+Enter for new line)"
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm resize-none min-h-[44px] max-h-32"
            disabled={isStreaming}
            rows={1}
          />
          {isStreaming ? (
            <button type="button" onClick={stop} className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-medium h-[44px]">
              Stop
            </button>
          ) : (
            <button type="submit" disabled={!input.trim()} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium h-[44px]">
              Send
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
