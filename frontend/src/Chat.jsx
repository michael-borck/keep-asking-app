import { useState, useRef, useEffect } from "react";

const API_URL = import.meta.env.VITE_API_URL || "";
const NUDGE_SEPARATOR = "\n\n---\n";

export default function Chat({ session }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [turnCount, setTurnCount] = useState(0);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Restore conversation history after page reload
  useEffect(() => {
    async function fetchHistory() {
      try {
        const res = await fetch(
          `${API_URL}/api/history/${session.sessionCode}`
        );
        if (res.ok) {
          const data = await res.json();
          if (data.messages.length > 0) {
            setMessages(data.messages);
            setTurnCount(data.turn_count);
          }
        }
      } catch {
        // Silent fail - just start fresh
      }
    }
    fetchHistory();
  }, [session.sessionCode]);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function parseResponse(text) {
    const idx = text.indexOf(NUDGE_SEPARATOR);
    if (idx === -1) {
      return { body: text, nudge: null };
    }
    return {
      body: text.substring(0, idx),
      nudge: text.substring(idx + NUDGE_SEPARATOR.length),
    };
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const message = input.trim();
    if (!message || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_code: session.sessionCode,
          message,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Chat request failed");
      }

      const data = await res.json();
      setTurnCount(data.turn_number);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.reply },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "system", content: `Error: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
      textareaRef.current?.focus();
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h2>AI Lab Session</h2>
        <span className="session-info">
          Session: {session.sessionCode}
        </span>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="message system">
            Your session is ready. Type your first message to begin working
            with the AI.
          </div>
        )}

        {messages.map((msg, i) => {
          if (msg.role === "user") {
            return (
              <div key={i} className="message user">
                {msg.content}
              </div>
            );
          }

          if (msg.role === "system") {
            return (
              <div key={i} className="message system">
                {msg.content}
              </div>
            );
          }

          const { body, nudge } = parseResponse(msg.content);
          return (
            <div key={i} className="message assistant">
              {body}
              {nudge && <span className="nudge">{nudge}</span>}
            </div>
          );
        })}

        {loading && (
          <div className="typing-indicator">AI is thinking...</div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <form className="chat-input-form" onSubmit={handleSubmit}>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
            rows={2}
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()}>
            Send
          </button>
        </form>
        <div className="turn-count">
          Turn {turnCount} | Session: {session.sessionCode}
        </div>
      </div>
    </div>
  );
}
