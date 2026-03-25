import { useState, useEffect } from 'react';
import { estimateTokens, type TokenEstimate } from '../../services/api';

interface TokenVisualizationProps {
  documentContent: string;
  model: string;
}

export default function TokenVisualization({ documentContent, model }: TokenVisualizationProps) {
  const [estimate, setEstimate] = useState<TokenEstimate>({
    document_tokens: 0,
    chunk_tokens: 0,
    total_tokens: 0,
    context_limit: 4096,
    usage_percent: 0,
  });

  useEffect(() => {
    const update = async () => {
      try {
        const est = await estimateTokens(documentContent, [], model);
        setEstimate(est);
      } catch {
        // Rough local estimate if backend is down
        const tokens = Math.ceil(documentContent.length / 4);
        const limit = 4096;
        setEstimate({
          document_tokens: tokens,
          chunk_tokens: 0,
          total_tokens: tokens,
          context_limit: limit,
          usage_percent: Math.min(100, (tokens / limit) * 100),
        });
      }
    };

    const timer = setTimeout(update, 500); // Debounce
    return () => clearTimeout(timer);
  }, [documentContent, model]);

  const isWarning = estimate.usage_percent > 80;

  return (
    <div className="token-viz">
      <span className="token-label">Tokens</span>
      <div className="token-bar-container">
        <div
          className={`token-bar-fill ${isWarning ? 'warning' : ''}`}
          style={{ width: `${Math.min(100, estimate.usage_percent)}%` }}
        />
      </div>
      <span className="token-label">
        {estimate.total_tokens.toLocaleString()} / {estimate.context_limit.toLocaleString()}
        {' '}({estimate.usage_percent.toFixed(0)}%)
      </span>
    </div>
  );
}
