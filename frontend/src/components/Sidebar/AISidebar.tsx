import { useState } from 'react';
import ChatPanel from './ChatPanel';
import FilesPanel from './FilesPanel';
import ModelSelector from './ModelSelector';
import TokenVisualization from './TokenVisualization';

interface AISidebarProps {
  selectedText: string;
  documentContent: string;
}

export default function AISidebar({ selectedText, documentContent }: AISidebarProps) {
  const [activeTab, setActiveTab] = useState<'chat' | 'files'>('chat');
  const [selectedModel, setSelectedModel] = useState('llama3');

  return (
    <aside className="sidebar">
      {/* Header with model selector */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <span style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-primary)' }}>
          🧠 Loomin AI
        </span>
        <ModelSelector selectedModel={selectedModel} onModelChange={setSelectedModel} />
      </div>

      {/* Tabs */}
      <div className="sidebar-tabs">
        <button
          className={`sidebar-tab ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          💬 Chat
        </button>
        <button
          className={`sidebar-tab ${activeTab === 'files' ? 'active' : ''}`}
          onClick={() => setActiveTab('files')}
        >
          📁 Files
        </button>
      </div>

      {/* Content */}
      {activeTab === 'chat' ? (
        <ChatPanel
          selectedText={selectedText}
          documentContent={documentContent}
          selectedModel={selectedModel}
        />
      ) : (
        <FilesPanel />
      )}

      {/* Token Visualization — always visible */}
      <TokenVisualization documentContent={documentContent} model={selectedModel} />
    </aside>
  );
}
