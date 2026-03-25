import { useState, useEffect } from 'react';
import { listModels, type OllamaModel } from '../../services/api';

interface ModelSelectorProps {
  selectedModel: string;
  onModelChange: (model: string) => void;
}

export default function ModelSelector({ selectedModel, onModelChange }: ModelSelectorProps) {
  const [models, setModels] = useState<OllamaModel[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const m = await listModels();
        setModels(m);
        if (m.length > 0 && !m.find(x => x.name === selectedModel)) {
          onModelChange(m[0].name);
        }
      } catch {
        // Ollama may not be running
      }
    };
    load();
    const interval = setInterval(load, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="model-selector">
      <select
        className="model-select"
        value={selectedModel}
        onChange={e => onModelChange(e.target.value)}
      >
        {models.length === 0 && (
          <option value={selectedModel}>{selectedModel} (offline)</option>
        )}
        {models.map(m => (
          <option key={m.name} value={m.name}>
            {m.name} {m.parameter_size ? `(${m.parameter_size})` : ''}
          </option>
        ))}
      </select>
    </div>
  );
}
