import { useState, useCallback, useEffect } from 'react';
import RichTextEditor from './components/Editor/RichTextEditor';
import AISidebar from './components/Sidebar/AISidebar';
import { checkHealth, saveEditorVersion } from './services/api';
import './index.css';

export default function App() {
  const [selectedText, setSelectedText] = useState('');
  const [documentContent, setDocumentContent] = useState('');
  const [backendOnline, setBackendOnline] = useState(false);
  const [saveStatus, setSaveStatus] = useState('');

  // Check backend health
  useEffect(() => {
    const check = async () => {
      const ok = await checkHealth();
      setBackendOnline(ok);
    };
    check();
    const interval = setInterval(check, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectionChange = useCallback((text: string) => {
    setSelectedText(text);
  }, []);

  const handleContentChange = useCallback((content: string) => {
    setDocumentContent(content);
  }, []);

  const handleSave = async () => {
    try {
      setSaveStatus('Saving…');
      await saveEditorVersion('Document', documentContent);
      setSaveStatus('Saved ✓');
      setTimeout(() => setSaveStatus(''), 2000);
    } catch {
      setSaveStatus('Save failed');
      setTimeout(() => setSaveStatus(''), 3000);
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="app-logo">
          <div className="app-logo-icon">L</div>
          <span className="app-logo-text">Loomin Docs</span>
        </div>
        <div className="app-header-actions">
          {saveStatus && (
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{saveStatus}</span>
          )}
          <button className="btn-ghost" onClick={handleSave}>
            💾 Save Version
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div className={`status-indicator ${backendOnline ? 'online' : 'offline'}`} />
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {backendOnline ? 'Connected' : 'Offline'}
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="app-main">
        {/* Editor */}
        <div className="editor-pane">
          <RichTextEditor
            onSelectionChange={handleSelectionChange}
            onContentChange={handleContentChange}
          />
        </div>

        {/* AI Sidebar */}
        <AISidebar
          selectedText={selectedText}
          documentContent={documentContent}
        />
      </main>
    </div>
  );
}
