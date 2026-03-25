import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { sendChat, type ChatResponse, type Citation, type LatencyMetadata } from '../../services/api';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  metadata?: LatencyMetadata;
}

interface ChatPanelProps {
  selectedText: string;
  documentContent: string;
  selectedModel: string;
}

export default function ChatPanel({ selectedText, documentContent, selectedModel }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [expandedCitation, setExpandedCitation] = useState<string | null>(null); // "msgIdx-citIdx"
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (message?: string, action?: string) => {
    const text = message || input.trim();
    if (!text && !action) return;

    const userMsg = action
      ? `[${action.toUpperCase()}] ${selectedText.slice(0, 100)}...`
      : text;

    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setInput('');
    setLoading(true);

    try {
      const res: ChatResponse = await sendChat(
        text,
        selectedModel,
        selectedText || undefined,
        action || undefined,
        documentContent || undefined
      );

      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: res.response,
          citations: res.citations,
          metadata: res.metadata,
        },
      ]);

      // If it was an "improve" action, replace the selected text in the editor
      if (action === 'improve' && (window as any).__editorReplaceSelection) {
        (window as any).__editorReplaceSelection(res.response);
      }
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: `⚠️ Error: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="sidebar-content">
      {/* Context Actions (visible when text is selected) */}
      {selectedText && (
        <div className="context-actions">
          <div className="has-selection-info">
            ✨ {selectedText.length} chars selected
          </div>
          <button
            className="context-btn"
            onClick={() => handleSend('Summarize this text', 'summarize')}
            disabled={loading}
          >
            Summarize
          </button>
          <button
            className="context-btn"
            onClick={() => handleSend('Improve this text', 'improve')}
            disabled={loading}
          >
            Improve
          </button>
        </div>
      )}

      {/* Messages */}
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">💬</div>
            <div className="empty-state-title">Loomin AI Assistant</div>
            <div className="empty-state-text">
              Ask me anything about your document, or select text and use Summarize / Improve.
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`chat-message ${msg.role}`}>
            <div className="chat-bubble">
              {msg.role === 'assistant' ? (
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              ) : (
                <p>{msg.content}</p>
              )}
            </div>

            {/* Citations — click to expand source chunk */}
            {msg.citations && msg.citations.length > 0 && (
              <div className="chat-citations">
                {msg.citations.map((c, ci) => {
                  const citKey = `${i}-${ci}`;
                  const isExpanded = expandedCitation === citKey;
                  return (
                    <div key={ci} className="citation-wrapper">
                      <div
                        className={`citation-chip ${isExpanded ? 'expanded' : ''}`}
                        onClick={() => setExpandedCitation(isExpanded ? null : citKey)}
                      >
                        <span className="citation-badge">{ci + 1}</span>
                        <span>{c.document_name}</span>
                        <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>
                          ({(c.score * 100).toFixed(0)}%)
                        </span>
                        <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-muted)' }}>
                          {isExpanded ? '▲' : '▼'}
                        </span>
                      </div>
                      {isExpanded && (
                        <div className="citation-content">
                          {c.content}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Latency Metadata */}
            {msg.metadata && (
              <div className="chat-metadata">
                <span className="meta-badge">⏱ {msg.metadata.total_time_ms.toFixed(0)}ms</span>
                <span className="meta-badge">🔍 {msg.metadata.retrieval_time_ms.toFixed(0)}ms</span>
                <span className="meta-badge">⚡ {msg.metadata.tokens_per_sec.toFixed(1)} tok/s</span>
                <span className="meta-badge">🎯 {msg.metadata.tokens_generated} tokens</span>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="chat-message assistant">
            <div className="chat-bubble">
              <div className="loading-dots">
                <span /><span /><span />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="chat-input-container">
        <div className="chat-input-wrapper">
          <textarea
            ref={inputRef}
            className="chat-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask Loomin about your documents…"
            rows={1}
            disabled={loading}
          />
          <button
            className="chat-send-btn"
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            title="Send"
          >
            ↑
          </button>
        </div>
      </div>
    </div>
  );
}
