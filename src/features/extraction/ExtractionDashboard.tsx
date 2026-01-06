import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ExtractionStatus } from './components/ExtractionStatus';
import { ExtractionHistory } from './components/ExtractionHistory';
import { ExtractedPropertyList } from './components/ExtractedPropertyList';
import { ExtractedPropertyDetail } from './components/ExtractedPropertyDetail';
import type { ExtractionRun } from '@/types/extraction';

export function ExtractionDashboard() {
  const navigate = useNavigate();
  const { propertyName } = useParams<{ propertyName: string }>();
  const [selectedRunId, setSelectedRunId] = useState<string | undefined>();

  const handlePropertyClick = (name: string) => {
    navigate(`/extraction/${encodeURIComponent(name)}`);
  };

  const handleBackToList = () => {
    navigate('/extraction');
  };

  const handleRunClick = (run: ExtractionRun) => {
    setSelectedRunId(run.id);
  };

  // If we have a property name in the URL, show the detail view
  if (propertyName) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-neutral-900">
            Extracted Data
          </h1>
          <p className="text-neutral-600 mt-1">
            View extracted underwriting model data for {decodeURIComponent(propertyName)}
          </p>
        </div>

        {/* Property Detail */}
        <ExtractedPropertyDetail
          propertyName={decodeURIComponent(propertyName)}
          runId={selectedRunId}
          onBack={handleBackToList}
        />
      </div>
    );
  }

  // Main dashboard view
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-neutral-900">
          UW Model Extraction
        </h1>
        <p className="text-neutral-600 mt-1">
          Extract and view underwriting model data from SharePoint Excel files
        </p>
      </div>

      {/* Top Section: Status */}
      <ExtractionStatus
        onRunClick={(runId) => setSelectedRunId(runId)}
      />

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Property List - Takes up 2 columns on large screens */}
        <div className="lg:col-span-2">
          <ExtractedPropertyList
            runId={selectedRunId}
            onPropertyClick={handlePropertyClick}
          />
        </div>

        {/* History - Takes up 1 column on large screens */}
        <div className="lg:col-span-1">
          <ExtractionHistory
            limit={5}
            onRunClick={handleRunClick}
          />
        </div>
      </div>
    </div>
  );
}
