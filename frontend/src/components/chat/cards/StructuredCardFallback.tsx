import React from 'react';
import { Layers } from 'lucide-react';
import { StructuredUIPayload } from '../../../types';

interface StructuredCardFallbackProps {
  payload: StructuredUIPayload;
}

export const StructuredCardFallback: React.FC<StructuredCardFallbackProps> = ({ payload }) => {
  const typeLabel = (payload.type || 'Custom Payload').replace(/_/g, ' ');

  return (
    <div className="structured-card structured-card-fallback" data-testid="structured-card-fallback">
      <div className="card-header-badge">
        <span className="badge badge-subtle">
          <Layers size={13} className="badge-icon" />
          <span>{typeLabel}</span>
        </span>
      </div>
      <div className="fallback-json-box">
        <pre>{JSON.stringify(payload, null, 2)}</pre>
      </div>
    </div>
  );
};
