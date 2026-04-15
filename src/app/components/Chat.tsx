"use client";

import { useChat } from "@ai-sdk/react";
import { TextStreamChatTransport } from "ai";
import { useCallback, useEffect, useRef, useState } from "react";
import { useMarkdownProcessor } from "@/app/hooks/use-markdown-processor";

// Assistant Message with Markdown
function AssistantMessage({
  content,
  isDark,
}: {
  content: string;
  isDark: boolean;
}) {
  const processedContent = useMarkdownProcessor(content, isDark);
  return <div className="text-sm">{processedContent}</div>;
}

export function Chat() {
  const [input, setInput] = useState("");
  const [darkMode, setDarkMode] = useState(true);

  const { messages, sendMessage, stop, status, error, setMessages } = useChat({
    transport: new TextStreamChatTransport({
      api: "/api/chat",
    }),
  });

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const isSubmitted = status === "submitted";
  const isStreaming = status === "streaming";

  // Auto-scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-focus textarea
  useEffect(() => {
    if (!isSubmitted  && textareaRef.current) {
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
    <div
      className={`flex flex-col h-screen ${darkMode ? "bg-neutral-950" : "bg-white"}`}
    >
      {/* Header */}
      <div
        className={`flex items-center justify-between px-4 py-3 border-b ${darkMode ? "border-neutral-800 bg-neutral-900" : "border-gray-200 bg-white"}`}
      >
        <h2
          className={`text-lg font-semibold ${darkMode ? "text-white" : "text-gray-900"}`}
        >
          Chat
        </h2>
        <div className="flex gap-2">
          <button
            onClick={() => setDarkMode(!darkMode)}
            className={`text-sm px-3 py-1 rounded transition-colors ${darkMode ? "bg-neutral-800 text-white hover:bg-neutral-700" : "bg-gray-200 text-gray-700 hover:bg-gray-300"}`}
            type="button"
          >
            {darkMode ? "☀️" : "🌙"}
          </button>
          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className={`text-sm transition-colors ${darkMode ? "text-neutral-400 hover:text-neutral-200" : "text-gray-500 hover:text-gray-700"}`}
              type="button"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className={`flex-1 overflow-y-auto p-4 space-y-4`}>
        {messages.length === 0 ? (
          <div
            className={`flex flex-col items-center justify-center h-full ${darkMode ? "text-gray-500" : "text-gray-400"}`}
          >
            <svg
              className="w-12 h-12 mb-3"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-label="Chat icon"
            >
              <title>Chat</title>
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
              />
            </svg>
            <p className="text-sm">Start a conversation</p>
          </div>
        ) : (
          <>
            {messages.map((message) => {
              const textContent =
                message.parts
                  ?.filter((part: any) => part.type === "text")
                  .map((part: any) => part.text)
                  .join("") || "";
              return (
                <div
                  key={message.id}
                  className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-2 ${
                      message.role === "user"
                        ? darkMode
                          ? "bg-neutral-700 text-white"
                          : "bg-blue-600 text-white"
                        : darkMode
                          ? "bg-neutral-900 text-neutral-100"
                          : "bg-gray-100 text-gray-900"
                    }`}
                  >
                    {message.role === "user" ? (
                      <p className="whitespace-pre-wrap text-sm">
                        {textContent}
                      </p>
                    ) : (
                      <AssistantMessage
                        content={textContent}
                        isDark={darkMode}
                      />
                    )}
                  </div>
                </div>
              );
            })}
          </>
        )}

        {error && (
          <div className="flex justify-center">
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 ${darkMode ? "bg-red-900 text-red-100" : "bg-red-100 text-red-900"}`}
            >
              <p className="text-sm">{error.message}</p>
            </div>
          </div>
        )}

        {isSubmitted && (
          <div className="flex justify-start">
            <div
              className={`rounded-lg px-4 py-2 ${darkMode ? "bg-neutral-900" : "bg-gray-100"}`}
            >
              <div className="flex space-x-1">
                <div
                  className={`w-2 h-2 rounded-full animate-bounce ${darkMode ? "bg-neutral-500" : "bg-gray-400"}`}
                  style={{ animationDelay: "0ms" }}
                />
                <div
                  className={`w-2 h-2 rounded-full animate-bounce ${darkMode ? "bg-neutral-500" : "bg-gray-400"}`}
                  style={{ animationDelay: "150ms" }}
                />
                <div
                  className={`w-2 h-2 rounded-full animate-bounce ${darkMode ? "bg-neutral-500" : "bg-gray-400"}`}
                  style={{ animationDelay: "300ms" }}
                />
              </div>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <div
        className={`border-t p-4 ${darkMode ? "border-neutral-800 bg-neutral-900" : "border-gray-200 bg-white"}`}
      >
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
            className={`flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 text-sm resize-none min-h-11 max-h-32 ${
              darkMode
                ? "border-neutral-700 bg-neutral-800 text-white placeholder-neutral-500 focus:ring-neutral-500"
                : "border-gray-300 bg-white text-gray-900 placeholder-gray-400 focus:ring-blue-500"
            }`}
            disabled={isStreaming}
            rows={3}
          />
          {isStreaming ? (
            <button
              type="button"
              onClick={stop}
              className={`px-4 py-2 text-white rounded-lg text-sm font-medium h-11 ${darkMode ? "bg-red-800 hover:bg-red-700" : "bg-red-600 hover:bg-red-700"}`}
            >
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className={`px-4 py-2 text-white rounded-lg disabled:opacity-50 text-sm font-medium h-11 ${darkMode ? "bg-neutral-700 hover:bg-neutral-600" : "bg-blue-600 hover:bg-blue-700"}`}
            >
              Send
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
