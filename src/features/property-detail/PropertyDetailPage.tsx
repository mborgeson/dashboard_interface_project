import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { mockProperties } from '@/data/mockProperties';
import { PropertyHero } from './components/PropertyHero';
import { OverviewTab } from './components/OverviewTab';
import { FinancialsTab } from './components/FinancialsTab';
import { OperationsTab } from './components/OperationsTab';
import { PerformanceTab } from './components/PerformanceTab';
import { TransactionsTab } from './components/TransactionsTab';

type Tab = 'overview' | 'financials' | 'operations' | 'performance' | 'transactions';

export function PropertyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  const property = mockProperties.find((p) => p.id === id);

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

      {/* Tab Content */}
      <div className="bg-gray-50 min-h-[600px]">
        {activeTab === 'overview' && <OverviewTab property={property} />}
        {activeTab === 'financials' && <FinancialsTab property={property} />}
        {activeTab === 'operations' && <OperationsTab property={property} />}
        {activeTab === 'performance' && <PerformanceTab property={property} />}
        {activeTab === 'transactions' && <TransactionsTab propertyId={property.id} />}
      </div>
    </div>
  );
}
