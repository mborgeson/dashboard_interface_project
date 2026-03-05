import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ExtractionStatus } from './components/ExtractionStatus';
import { ExtractionHistory } from './components/ExtractionHistory';
import { ExtractedPropertyList } from './components/ExtractedPropertyList';
import { ExtractedPropertyDetail } from './components/ExtractedPropertyDetail';
import { GroupPipelineTab } from './components/GroupPipelineTab';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { ErrorState } from '@/components/ui/error-state';
import type { ExtractionRun } from '@/types/extraction';

type Tab = 'quick' | 'pipeline';

export function ExtractionDashboard() {
  const navigate = useNavigate();
  const { propertyName } = useParams<{ propertyName: string }>();
  const [selectedRunId, setSelectedRunId] = useState<string | undefined>();
  const [activeTab, setActiveTab] = useState<Tab>('quick');

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

      {/* Tab Navigation */}
      <div className="border-b border-neutral-200">
        <nav className="-mb-px flex gap-6">
          <button
            onClick={() => setActiveTab('quick')}
            className={`py-3 px-1 border-b-2 text-sm font-medium transition-colors ${
              activeTab === 'quick'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300'
            }`}
          >
            Quick Extraction
          </button>
          <button
            onClick={() => setActiveTab('pipeline')}
            className={`py-3 px-1 border-b-2 text-sm font-medium transition-colors ${
              activeTab === 'pipeline'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300'
            }`}
          >
            Group Pipeline
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'quick' ? (
        <>
          {/* Top Section: Status */}
          <ErrorBoundary
            fallback={
              <ErrorState
                title="Failed to load extraction status"
                description="Unable to display the extraction status. Please try again."
                onRetry={() => window.location.reload()}
              />
            }
          >
            <ExtractionStatus
              onRunClick={(runId) => setSelectedRunId(runId)}
            />
          </ErrorBoundary>

          {/* Main Content Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Property List - Takes up 2 columns on large screens */}
            <div className="lg:col-span-2">
              <ErrorBoundary
                fallback={
                  <ErrorState
                    title="Failed to load properties"
                    description="Unable to display extracted properties. Please try again."
                    onRetry={() => window.location.reload()}
                  />
                }
              >
                <ExtractedPropertyList
                  runId={selectedRunId}
                  onPropertyClick={handlePropertyClick}
                />
              </ErrorBoundary>
            </div>

            {/* History - Takes up 1 column on large screens */}
            <div className="lg:col-span-1">
              <ErrorBoundary
                fallback={
                  <ErrorState
                    title="Failed to load extraction history"
                    description="Unable to display extraction history. Please try again."
                    onRetry={() => window.location.reload()}
                  />
                }
              >
                <ExtractionHistory
                  limit={5}
                  onRunClick={handleRunClick}
                />
              </ErrorBoundary>
            </div>
          </div>
        </>
      ) : (
        <ErrorBoundary
          fallback={
            <ErrorState
              title="Failed to load group pipeline"
              description="Unable to display the group pipeline. Please try again."
              onRetry={() => window.location.reload()}
            />
          }
        >
          <GroupPipelineTab />
        </ErrorBoundary>
      )}
    </div>
  );
}
