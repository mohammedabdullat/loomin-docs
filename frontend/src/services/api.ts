/* ═══════════════════════════════════════════════════════════════════
   Loomin-Docs API Client
   ═══════════════════════════════════════════════════════════════════ */

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ─── Types ──────────────────────────────────────────────────────────
export interface Citation {
  chunk_id: string;
  document_name: string;
  content: string;
  score: number;
}

export interface LatencyMetadata {
  request_id: string;
  retrieval_time_ms: number;
  generation_time_ms: number;
  tokens_generated: number;
  tokens_per_sec: number;
  total_time_ms: number;
}

export interface ChatResponse {
  response: string;
  citations: Citation[];
  metadata: LatencyMetadata;
}

export interface DocumentInfo {
  id: string;
  filename: string;
  file_type: string;
  chunk_count: number;
  uploaded_at: string;
  size_bytes: number;
}

export interface OllamaModel {
  name: string;
  size: string;
  parameter_size: string;
  context_length: number;
}

export interface EditorVersion {
  id: string;
  title: string;
  content: string;
  created_at: string;
  word_count: number;
}

export interface TokenEstimate {
  document_tokens: number;
  chunk_tokens: number;
  total_tokens: number;
  context_limit: number;
  usage_percent: number;
}

// ─── Chat ────────────────────────────────────────────────────────────
export async function sendChat(
  message: string,
  model: string,
  selectedText?: string,
  action?: string,
  documentContent?: string
): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      model,
      selected_text: selectedText,
      action,
      document_content: documentContent,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Chat request failed');
  }
  return res.json();
}

export async function getChatHistory(): Promise<{ messages: any[] }> {
  const res = await fetch(`${BASE}/api/chat/history`);
  return res.json();
}

// ─── Documents ──────────────────────────────────────────────────────
export async function uploadDocument(file: File): Promise<DocumentInfo> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/api/documents/upload`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export async function listDocuments(): Promise<DocumentInfo[]> {
  const res = await fetch(`${BASE}/api/documents`);
  const data = await res.json();
  return data.documents || [];
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetch(`${BASE}/api/documents/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Delete failed');
}

// ─── Editor ─────────────────────────────────────────────────────────
export async function saveEditorVersion(title: string, content: string): Promise<EditorVersion> {
  const res = await fetch(`${BASE}/api/editor/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, content }),
  });
  return res.json();
}

export async function listEditorVersions(): Promise<EditorVersion[]> {
  const res = await fetch(`${BASE}/api/editor/versions`);
  const data = await res.json();
  return data.versions || [];
}

export async function getEditorVersion(id: string): Promise<EditorVersion> {
  const res = await fetch(`${BASE}/api/editor/versions/${id}`);
  return res.json();
}

// ─── Models ─────────────────────────────────────────────────────────
export async function listModels(): Promise<OllamaModel[]> {
  const res = await fetch(`${BASE}/api/models`);
  const data = await res.json();
  return data.models || [];
}

// ─── Tokens ─────────────────────────────────────────────────────────
export async function estimateTokens(
  documentContent: string,
  retrievedChunks: string[],
  model: string
): Promise<TokenEstimate> {
  const res = await fetch(`${BASE}/api/tokens/estimate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      document_content: documentContent,
      retrieved_chunks: retrievedChunks,
      model,
    }),
  });
  return res.json();
}

// ─── Health ─────────────────────────────────────────────────────────
export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/api/health`);
    return res.ok;
  } catch {
    return false;
  }
}
