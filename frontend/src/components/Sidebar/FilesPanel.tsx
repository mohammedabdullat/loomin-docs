import { useState, useRef, useEffect, useCallback } from 'react';
import { uploadDocument, listDocuments, deleteDocument, type DocumentInfo } from '../../services/api';

export default function FilesPanel() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadDocs = useCallback(async () => {
    try {
      const docs = await listDocuments();
      setDocuments(docs);
    } catch {
      // Backend may not be running
    }
  }, []);

  useEffect(() => { loadDocs(); }, [loadDocs]);

  const handleUpload = async (files: FileList | null) => {
    if (!files) return;
    setUploading(true);
    setError('');

    for (const file of Array.from(files)) {
      try {
        await uploadDocument(file);
      } catch (err: any) {
        setError(err.message);
      }
    }

    setUploading(false);
    loadDocs();
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteDocument(id);
      loadDocs();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'pdf': return '📄';
      case 'md': return '📝';
      case 'txt': return '📃';
      default: return '📎';
    }
  };

  return (
    <div className="files-panel">
      {/* Drop Zone */}
      <div
        className={`file-drop-zone ${dragOver ? 'drag-over' : ''}`}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => { e.preventDefault(); setDragOver(false); handleUpload(e.dataTransfer.files); }}
        onClick={() => fileInputRef.current?.click()}
      >
        <div className="file-drop-icon">{uploading ? '⏳' : '📁'}</div>
        <div className="file-drop-text">
          {uploading ? 'Uploading…' : <>Drop files here or <strong>browse</strong></>}
        </div>
        <div className="file-drop-hint">.pdf, .md, .txt — up to 50 MB</div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.md,.txt"
          multiple
          style={{ display: 'none' }}
          onChange={e => handleUpload(e.target.files)}
        />
      </div>

      {error && (
        <div style={{ padding: '0 16px', color: 'var(--error)', fontSize: 13 }}>
          ⚠️ {error}
        </div>
      )}

      {/* File List */}
      <div className="file-list">
        {documents.length === 0 && !uploading && (
          <div className="empty-state">
            <div className="empty-state-icon">📂</div>
            <div className="empty-state-title">No files yet</div>
            <div className="empty-state-text">
              Upload documents to use as RAG context for the AI assistant.
            </div>
          </div>
        )}

        {documents.map(doc => (
          <div key={doc.id} className="file-item">
            <div className={`file-icon ${doc.file_type}`}>
              {getFileIcon(doc.file_type)}
            </div>
            <div className="file-info">
              <div className="file-name">{doc.filename}</div>
              <div className="file-meta">
                {doc.chunk_count} chunks · {formatSize(doc.size_bytes)}
              </div>
            </div>
            <button
              className="file-delete-btn"
              onClick={() => handleDelete(doc.id)}
              title="Delete"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
