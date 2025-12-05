import { useState } from 'react';
import {
  FileText,
  Hammer,
  ListTodo,
  Send,
  Settings,
  Plus,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { ReportTemplates } from './components/ReportTemplates';
import { CustomReportBuilder } from './components/CustomReportBuilder';
import { ReportQueue } from './components/ReportQueue';
import { Distribution } from './components/Distribution';
import { ReportSettings } from './components/ReportSettings';

type TabId = 'templates' | 'builder' | 'queue' | 'distribution' | 'settings';

interface Tab {
  id: TabId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
}

const tabs: Tab[] = [
  {
    id: 'templates',
    label: 'Report Templates',
    icon: FileText,
    description: 'Pre-built report templates',
  },
  {
    id: 'builder',
    label: 'Custom Builder',
    icon: Hammer,
    description: 'Drag-and-drop report builder',
  },
  {
    id: 'queue',
    label: 'Report Queue',
    icon: ListTodo,
    description: 'View and manage report generation',
  },
  {
    id: 'distribution',
    label: 'Distribution',
    icon: Send,
    description: 'Schedule and send reports',
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: Settings,
    description: 'Configure report defaults',
  },
];

export function ReportingSuitePage() {
  const [activeTab, setActiveTab] = useState<TabId>('templates');

  const renderContent = () => {
    switch (activeTab) {
      case 'templates':
        return <ReportTemplates />;
      case 'builder':
        return <CustomReportBuilder />;
      case 'queue':
        return <ReportQueue />;
      case 'distribution':
        return <Distribution />;
      case 'settings':
        return <ReportSettings />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Page Header */}
      <div className="bg-white border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-neutral-900">Reporting Suite</h1>
              <p className="text-sm text-neutral-500 mt-1">
                Generate, customize, and distribute professional reports for portfolio analysis and investor communications
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                className={cn(
                  'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  'bg-primary-600 text-white hover:bg-primary-700'
                )}
                onClick={() => setActiveTab('builder')}
              >
                <Plus className="w-4 h-4" />
                <span>New Report</span>
              </button>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="mt-6 flex items-center gap-1 border-b border-neutral-200 -mb-px">
            {tabs.map(tab => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;

              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                    isActive
                      ? 'border-primary-500 text-primary-700 bg-primary-50/50'
                      : 'border-transparent text-neutral-600 hover:text-neutral-900 hover:bg-neutral-50'
                  )}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Tab Content */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        {renderContent()}
      </div>
    </div>
  );
}

export default ReportingSuitePage;
