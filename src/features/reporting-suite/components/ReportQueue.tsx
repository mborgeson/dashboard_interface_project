import { useState, useEffect } from 'react';
import {
  Download,
  RefreshCw,
  Trash2,
  AlertCircle,
  CheckCircle,
  Clock,
  Loader2,
  FileText,
  FileSpreadsheet,
  Presentation,
  Search,
  Filter,
  Eye,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useQueuedReports,
  type QueuedReport,
} from '@/hooks/api/useReporting';

type StatusFilter = 'all' | QueuedReport['status'];

const statusConfig: Record<
  QueuedReport['status'],
  { label: string; color: string; icon: React.ComponentType<{ className?: string }> }
> = {
  pending: { label: 'Pending', color: 'bg-neutral-100 text-neutral-700', icon: Clock },
  generating: { label: 'Generating', color: 'bg-blue-100 text-blue-700', icon: Loader2 },
  completed: { label: 'Completed', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  failed: { label: 'Failed', color: 'bg-red-100 text-red-700', icon: AlertCircle },
};

const formatIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  pdf: FileText,
  excel: FileSpreadsheet,
  pptx: Presentation,
};

export function ReportQueue() {
  // Fetch queued reports from API (with mock fallback)
  const { data: queueData } = useQueuedReports();
  const [reports, setReports] = useState<QueuedReport[]>([]);

  // Sync API data into local state for optimistic updates
  useEffect(() => {
    if (queueData?.reports) setReports(queueData.reports);
  }, [queueData?.reports]);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedReport, setSelectedReport] = useState<QueuedReport | null>(null);

  const filteredReports = reports.filter(report => {
    const matchesSearch =
      report.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      report.templateName.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || report.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleRetry = (reportId: string) => {
    setReports(reports.map(r => (r.id === reportId ? { ...r, status: 'pending' as const, progress: 0, error: undefined } : r)));
  };

  const handleDelete = (reportId: string) => {
    setReports(reports.filter(r => r.id !== reportId));
  };

  const handleDownload = (report: QueuedReport) => {
    if (report.downloadUrl) {
      const link = document.createElement('a');
      link.href = report.downloadUrl;
      link.download = `${report.name}.${report.format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const getTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) return `${diffDays}d ago`;
    if (diffHours > 0) return `${diffHours}h ago`;
    if (diffMins > 0) return `${diffMins}m ago`;
    return 'Just now';
  };

  const pendingCount = reports.filter(r => r.status === 'pending').length;
  const generatingCount = reports.filter(r => r.status === 'generating').length;
  const completedCount = reports.filter(r => r.status === 'completed').length;
  const failedCount = reports.filter(r => r.status === 'failed').length;

  return (
    <div className="space-y-6">
      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-neutral-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-neutral-100 rounded-lg">
              <Clock className="w-5 h-5 text-neutral-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-neutral-900">{pendingCount}</p>
              <p className="text-sm text-neutral-500">Pending</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg border border-neutral-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
            </div>
            <div>
              <p className="text-2xl font-bold text-neutral-900">{generatingCount}</p>
              <p className="text-sm text-neutral-500">Generating</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg border border-neutral-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-neutral-900">{completedCount}</p>
              <p className="text-sm text-neutral-500">Completed</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg border border-neutral-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-neutral-900">{failedCount}</p>
              <p className="text-sm text-neutral-500">Failed</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
            <input
              type="text"
              placeholder="Search reports..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value as StatusFilter)}
              className="pl-10 pr-8 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 appearance-none bg-white"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="generating">Generating</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>

        <button
          onClick={() => window.location.reload()}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Reports Table */}
      <div className="bg-white rounded-lg border border-neutral-200">
        <table className="w-full">
          <thead>
            <tr className="border-b border-neutral-200 bg-neutral-50">
              <th className="text-left px-4 py-3 text-sm font-medium text-neutral-700">Report</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-neutral-700">Template</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-neutral-700">Status</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-neutral-700">Format</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-neutral-700">Requested</th>
              <th className="text-right px-4 py-3 text-sm font-medium text-neutral-700">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredReports.map(report => {
              const status = statusConfig[report.status];
              const StatusIcon = status.icon;
              const FormatIcon = formatIcons[report.format];

              return (
                <tr key={report.id} className="border-b border-neutral-100 hover:bg-neutral-50">
                  <td className="px-4 py-4">
                    <div>
                      <p className="font-medium text-neutral-900">{report.name}</p>
                      <p className="text-xs text-neutral-500">by {report.requestedBy}</p>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <span className="text-sm text-neutral-600">{report.templateName}</span>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-2">
                      <span
                        className={cn('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium', status.color)}
                      >
                        <StatusIcon className={cn('w-3.5 h-3.5', report.status === 'generating' && 'animate-spin')} />
                        {status.label}
                      </span>
                      {report.status === 'generating' && (
                        <span className="text-xs text-neutral-500">{report.progress}%</span>
                      )}
                    </div>
                    {report.status === 'generating' && (
                      <div className="mt-2 w-32 h-1.5 bg-neutral-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 rounded-full transition-all duration-300"
                          style={{ width: `${report.progress}%` }}
                        />
                      </div>
                    )}
                    {report.error && <p className="text-xs text-red-600 mt-1 max-w-xs truncate">{report.error}</p>}
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-1.5">
                      <FormatIcon className="w-4 h-4 text-neutral-500" />
                      <span className="text-sm text-neutral-600 uppercase">{report.format}</span>
                      {report.fileSize && <span className="text-xs text-neutral-400">({report.fileSize})</span>}
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div>
                      <p className="text-sm text-neutral-600">{getTimeAgo(report.requestedAt)}</p>
                      {report.completedAt && (
                        <p className="text-xs text-neutral-400">Completed {getTimeAgo(report.completedAt)}</p>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center justify-end gap-1">
                      {report.status === 'completed' && (
                        <button
                          onClick={() => handleDownload(report)}
                          className="p-2 text-primary-600 hover:bg-primary-50 rounded-md transition-colors"
                          title="Download"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                      )}
                      {report.status === 'failed' && (
                        <button
                          onClick={() => handleRetry(report.id)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
                          title="Retry"
                        >
                          <RefreshCw className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={() => setSelectedReport(report)}
                        className="p-2 text-neutral-600 hover:bg-neutral-100 rounded-md transition-colors"
                        title="View Details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(report.id)}
                        className="p-2 text-neutral-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filteredReports.length === 0 && (
          <div className="p-12 text-center">
            <FileText className="w-12 h-12 text-neutral-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-neutral-900 mb-1">No reports in queue</h3>
            <p className="text-neutral-500">Generate a report from the templates to see it here</p>
          </div>
        )}
      </div>

      {/* Report Detail Modal */}
      {selectedReport && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedReport(null)}>
          <div className="bg-white rounded-xl max-w-lg w-full" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-neutral-200">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-neutral-900">{selectedReport.name}</h2>
                  <p className="text-sm text-neutral-500 mt-1">Template: {selectedReport.templateName}</p>
                </div>
                <button onClick={() => setSelectedReport(null)} className="text-neutral-400 hover:text-neutral-600">
                  <span className="sr-only">Close</span>
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-neutral-500">Status</p>
                  <span
                    className={cn(
                      'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium mt-1',
                      statusConfig[selectedReport.status].color
                    )}
                  >
                    {statusConfig[selectedReport.status].label}
                  </span>
                </div>
                <div>
                  <p className="text-sm text-neutral-500">Format</p>
                  <p className="font-medium text-neutral-900 uppercase">{selectedReport.format}</p>
                </div>
                <div>
                  <p className="text-sm text-neutral-500">Requested By</p>
                  <p className="font-medium text-neutral-900">{selectedReport.requestedBy}</p>
                </div>
                <div>
                  <p className="text-sm text-neutral-500">Requested At</p>
                  <p className="font-medium text-neutral-900">{new Date(selectedReport.requestedAt).toLocaleString()}</p>
                </div>
                {selectedReport.completedAt && (
                  <>
                    <div>
                      <p className="text-sm text-neutral-500">Completed At</p>
                      <p className="font-medium text-neutral-900">{new Date(selectedReport.completedAt).toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-sm text-neutral-500">File Size</p>
                      <p className="font-medium text-neutral-900">{selectedReport.fileSize}</p>
                    </div>
                  </>
                )}
              </div>

              {selectedReport.error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-700">{selectedReport.error}</p>
                </div>
              )}

              {selectedReport.status === 'completed' && (
                <button
                  onClick={() => handleDownload(selectedReport)}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  Download Report
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
