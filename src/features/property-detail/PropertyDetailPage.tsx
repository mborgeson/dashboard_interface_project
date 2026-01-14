import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { useProperty } from '@/hooks/api/useProperties';
import { PropertyHero } from './components/PropertyHero';
import { OverviewTab } from './components/OverviewTab';
import { FinancialsTab } from './components/FinancialsTab';
import { OperationsTab } from './components/OperationsTab';
import { PerformanceTab } from './components/PerformanceTab';
import { TransactionsTab } from './components/TransactionsTab';
import { PropertyActivityFeed } from './components/PropertyActivityFeed';

type Tab = 'overview' | 'financials' | 'operations' | 'performance' | 'transactions';

export function PropertyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  // Fetch property from API
  const { data: property, isLoading, error } = useProperty(id);

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        {/* Back Navigation */}
        <button
          onClick={() => navigate('/investments')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Investments
        </button>

        {/* Loading Skeleton */}
        <div className="flex flex-col items-center justify-center min-h-[400px]">
          <Loader2 className="w-12 h-12 text-primary-500 animate-spin mb-4" />
          <p className="text-gray-600">Loading property details...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        {/* Back Navigation */}
        <button
          onClick={() => navigate('/investments')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Investments
        </button>

        <div className="flex flex-col items-center justify-center min-h-[400px]">
          <h2 className="text-2xl font-semibold text-red-800 mb-2">Error Loading Property</h2>
          <p className="text-red-600 mb-4">
            {error instanceof Error ? error.message : 'Failed to load property details'}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Property not found
  if (!property) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">Property Not Found</h2>
        <p className="text-gray-600 mb-4">The property you're looking for doesn't exist.</p>
        <button
          onClick={() => navigate('/investments')}
          className="flex items-center gap-2 text-primary-600 hover:text-primary-700"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Investments
        </button>
      </div>
    );
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'financials', label: 'Financials' },
    { id: 'operations', label: 'Operations' },
    { id: 'performance', label: 'Performance' },
    { id: 'transactions', label: 'Transactions' },
  ];

  return (
    <div className="space-y-6">
      {/* Back Navigation */}
      <button
        onClick={() => navigate('/investments')}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Investments
      </button>

      {/* Hero Section */}
      <PropertyHero property={property} />

      {/* Tabs */}
      <div className="bg-white border-b">
        <div className="flex gap-8 px-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-4 px-2 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content with Activity Feed Sidebar */}
      <div className="bg-gray-50 min-h-[600px]">
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-6 p-6">
          {/* Main Tab Content */}
          <div className="min-w-0">
            {activeTab === 'overview' && <OverviewTab property={property} />}
            {activeTab === 'financials' && <FinancialsTab property={property} />}
            {activeTab === 'operations' && <OperationsTab property={property} />}
            {activeTab === 'performance' && <PerformanceTab property={property} />}
            {activeTab === 'transactions' && <TransactionsTab propertyId={property.id} />}
          </div>

          {/* Activity Feed Sidebar */}
          <aside className="xl:sticky xl:top-6 xl:self-start">
            <PropertyActivityFeed
              propertyId={property.id}
              maxItems={15}
              collapsible
              enableRealtime
            />
          </aside>
        </div>
      </div>
    </div>
  );
}
