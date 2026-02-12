import { useState, useRef } from 'react';
import {
  Send,
  Plus,
  Trash2,
  Edit2,
  Calendar,
  Clock,
  Mail,
  Users,
  FileText,
  FileSpreadsheet,
  Presentation,
  Play,
  Pause,
  CheckCircle,
  Search,
  Filter,
  Loader2,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useDistributionSchedules,
  useReportTemplates,
  useCreateDistributionSchedule,
  useUpdateDistributionSchedule,
  useDeleteDistributionSchedule,
  useGenerateReport,
  type DistributionSchedule,
  type ScheduleFrequency,
  type ReportFormat,
} from '@/hooks/api/useReporting';
import { useToast } from '@/hooks/useToast';

type FrequencyFilter = 'all' | DistributionSchedule['frequency'];

const frequencyLabels: Record<DistributionSchedule['frequency'], string> = {
  daily: 'Daily',
  weekly: 'Weekly',
  monthly: 'Monthly',
  quarterly: 'Quarterly',
};

const frequencyColors: Record<DistributionSchedule['frequency'], string> = {
  daily: 'bg-blue-100 text-blue-700',
  weekly: 'bg-green-100 text-green-700',
  monthly: 'bg-purple-100 text-purple-700',
  quarterly: 'bg-amber-100 text-amber-700',
};

const formatIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  pdf: FileText,
  excel: FileSpreadsheet,
  pptx: Presentation,
};

const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

export function Distribution() {
  // Fetch distribution schedules and templates from API (with mock fallback)
  const { data: scheduleData, isLoading, error, refetch } = useDistributionSchedules();
  const { data: templateData } = useReportTemplates();
  const templates = templateData?.templates ?? [];
  const [localOverrides, setLocalOverrides] = useState<Record<string, Partial<DistributionSchedule> | null>>({});

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-primary-600 mr-2" />
        <span className="text-sm text-neutral-500">Loading schedules...</span>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <AlertCircle className="w-8 h-8 text-red-500" />
        <p className="text-sm text-red-600">
          {error instanceof Error ? error.message : 'Failed to load schedules'}
        </p>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Retry
        </button>
      </div>
    );
  }

  // Derive schedules from API data with local optimistic overrides
  const schedules = (scheduleData?.schedules ?? [])
    .filter(s => localOverrides[s.id] !== null)
    .map(s => (localOverrides[s.id] ? { ...s, ...localOverrides[s.id] } as DistributionSchedule : s));
  const [searchQuery, setSearchQuery] = useState('');
  const [frequencyFilter, setFrequencyFilter] = useState<FrequencyFilter>('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<DistributionSchedule | null>(null);

  const filteredSchedules = schedules.filter(schedule => {
    const matchesSearch =
      schedule.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      schedule.templateName.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFrequency = frequencyFilter === 'all' || schedule.frequency === frequencyFilter;
    return matchesSearch && matchesFrequency;
  });

  const { success, error: showError } = useToast();
  const createSchedule = useCreateDistributionSchedule();
  const updateSchedule = useUpdateDistributionSchedule();
  const deleteSchedule = useDeleteDistributionSchedule();
  const generateReport = useGenerateReport();

  // Form refs for modal
  const nameRef = useRef<HTMLInputElement>(null);
  const templateRef = useRef<HTMLSelectElement>(null);
  const frequencyRef = useRef<HTMLSelectElement>(null);
  const timeRef = useRef<HTMLInputElement>(null);
  const formatRef = useRef<string>('pdf');
  const recipientsRef = useRef<HTMLTextAreaElement>(null);

  const activeCount = schedules.filter(s => s.isActive).length;
  const inactiveCount = schedules.filter(s => !s.isActive).length;

  const handleToggleActive = (scheduleId: string) => {
    const schedule = schedules.find(s => s.id === scheduleId);
    if (!schedule) return;
    const newActive = !schedule.isActive;
    setLocalOverrides(prev => ({ ...prev, [scheduleId]: { isActive: newActive } }));
    updateSchedule.mutate(
      { id: Number(scheduleId), is_active: newActive },
      { onError: () => showError('Failed to update schedule') }
    );
  };

  const handleDeleteSchedule = (scheduleId: string) => {
    setLocalOverrides(prev => ({ ...prev, [scheduleId]: null }));
    deleteSchedule.mutate(Number(scheduleId), {
      onError: () => showError('Failed to delete schedule'),
    });
  };

  const handleSendNow = (schedule: DistributionSchedule) => {
    generateReport.mutate(
      {
        template_id: Number(schedule.templateId),
        name: `${schedule.name} - Immediate Send`,
        format: schedule.format as ReportFormat,
      },
      {
        onSuccess: () => success('Report queued for immediate delivery', { description: 'Check the Queue tab' }),
        onError: () => showError('Failed to send report'),
      }
    );
  };

  const getScheduleDescription = (schedule: DistributionSchedule) => {
    switch (schedule.frequency) {
      case 'daily':
        return `Every day at ${schedule.time}`;
      case 'weekly':
        return `Every ${dayNames[schedule.dayOfWeek || 0]} at ${schedule.time}`;
      case 'monthly':
        return `Day ${schedule.dayOfMonth} of each month at ${schedule.time}`;
      case 'quarterly':
        return `Day ${schedule.dayOfMonth} each quarter at ${schedule.time}`;
      default:
        return schedule.time;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="space-y-6">
      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border border-neutral-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-100 rounded-lg">
              <Calendar className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-neutral-900">{schedules.length}</p>
              <p className="text-sm text-neutral-500">Total Schedules</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg border border-neutral-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-neutral-900">{activeCount}</p>
              <p className="text-sm text-neutral-500">Active</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg border border-neutral-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-neutral-100 rounded-lg">
              <Pause className="w-5 h-5 text-neutral-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-neutral-900">{inactiveCount}</p>
              <p className="text-sm text-neutral-500">Paused</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters and Actions */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
            <input
              type="text"
              placeholder="Search schedules..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
            <select
              value={frequencyFilter}
              onChange={e => setFrequencyFilter(e.target.value as FrequencyFilter)}
              className="pl-10 pr-8 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 appearance-none bg-white"
            >
              <option value="all">All Frequencies</option>
              {Object.entries(frequencyLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Schedule
        </button>
      </div>

      {/* Schedules List */}
      <div className="space-y-3">
        {filteredSchedules.map(schedule => {
          const FormatIcon = formatIcons[schedule.format];
          return (
            <div
              key={schedule.id}
              className={cn(
                'bg-white rounded-lg border p-4 transition-all',
                schedule.isActive ? 'border-neutral-200' : 'border-neutral-200 bg-neutral-50'
              )}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  {/* Status Toggle */}
                  <button
                    onClick={() => handleToggleActive(schedule.id)}
                    className={cn(
                      'mt-1 p-2 rounded-lg transition-colors',
                      schedule.isActive
                        ? 'bg-green-100 text-green-600 hover:bg-green-200'
                        : 'bg-neutral-100 text-neutral-400 hover:bg-neutral-200'
                    )}
                    title={schedule.isActive ? 'Pause Schedule' : 'Activate Schedule'}
                  >
                    {schedule.isActive ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
                  </button>

                  {/* Schedule Info */}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-neutral-900">{schedule.name}</h3>
                      <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', frequencyColors[schedule.frequency])}>
                        {frequencyLabels[schedule.frequency]}
                      </span>
                      {!schedule.isActive && (
                        <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-neutral-200 text-neutral-600">
                          Paused
                        </span>
                      )}
                    </div>

                    <p className="text-sm text-neutral-600 mb-2">
                      Template: {schedule.templateName}
                    </p>

                    <div className="flex items-center gap-4 text-sm text-neutral-500">
                      <div className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        <span>{getScheduleDescription(schedule)}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Users className="w-4 h-4" />
                        <span>{schedule.recipients.length} recipients</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <FormatIcon className="w-4 h-4" />
                        <span className="uppercase">{schedule.format}</span>
                      </div>
                    </div>

                    {/* Recipients Preview */}
                    <div className="mt-2 flex items-center gap-2">
                      <Mail className="w-4 h-4 text-neutral-400" />
                      <span className="text-sm text-neutral-500">
                        {schedule.recipients.slice(0, 2).join(', ')}
                        {schedule.recipients.length > 2 && ` +${schedule.recipients.length - 2} more`}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Next/Last Send Info */}
                <div className="text-right text-sm">
                  {schedule.lastSent && (
                    <div className="text-neutral-500 mb-1">
                      Last sent: {formatDate(schedule.lastSent)}
                    </div>
                  )}
                  <div className="text-neutral-700 font-medium">
                    Next: {formatDate(schedule.nextScheduled)}
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="mt-4 pt-3 border-t border-neutral-100 flex items-center justify-end gap-2">
                <button
                  onClick={() => handleSendNow(schedule)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-primary-600 hover:bg-primary-50 rounded-md transition-colors"
                >
                  <Send className="w-4 h-4" />
                  Send Now
                </button>
                <button
                  onClick={() => setEditingSchedule(schedule)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-neutral-600 hover:bg-neutral-100 rounded-md transition-colors"
                >
                  <Edit2 className="w-4 h-4" />
                  Edit
                </button>
                <button
                  onClick={() => handleDeleteSchedule(schedule.id)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 rounded-md transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Empty State */}
      {filteredSchedules.length === 0 && (
        <div className="bg-white rounded-lg border border-neutral-200 p-12 text-center">
          <Calendar className="w-12 h-12 text-neutral-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-neutral-900 mb-1">No schedules found</h3>
          <p className="text-neutral-500 mb-4">Create a distribution schedule to automatically send reports</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Schedule
          </button>
        </div>
      )}

      {/* Create/Edit Modal */}
      {(showCreateModal || editingSchedule) && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => {
            setShowCreateModal(false);
            setEditingSchedule(null);
          }}
        >
          <div
            className="bg-white rounded-xl max-w-lg w-full max-h-[80vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}
          >
            <div className="p-6 border-b border-neutral-200">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-neutral-900">
                  {editingSchedule ? 'Edit Schedule' : 'Create Distribution Schedule'}
                </h2>
                <button
                  onClick={() => {
                    setShowCreateModal(false);
                    setEditingSchedule(null);
                  }}
                  className="text-neutral-400 hover:text-neutral-600"
                >
                  <span className="sr-only">Close</span>
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">Schedule Name</label>
                <input
                  ref={nameRef}
                  type="text"
                  defaultValue={editingSchedule?.name || ''}
                  placeholder="e.g., Weekly Executive Update"
                  className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">Report Template</label>
                <select
                  ref={templateRef}
                  defaultValue={editingSchedule?.templateId || ''}
                  className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">Select a template</option>
                  {templates.map(template => (
                    <option key={template.id} value={template.id}>
                      {template.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">Frequency</label>
                  <select
                    ref={frequencyRef}
                    defaultValue={editingSchedule?.frequency || 'weekly'}
                    className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    {Object.entries(frequencyLabels).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">Time</label>
                  <input
                    ref={timeRef}
                    type="time"
                    defaultValue={editingSchedule?.time || '09:00'}
                    className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">Format</label>
                <div className="flex gap-2">
                  {(['pdf', 'excel', 'pptx'] as const).map(format => {
                    const Icon = formatIcons[format];
                    return (
                      <button
                        key={format}
                        className={cn(
                          'flex items-center gap-2 px-4 py-2 border rounded-lg transition-colors',
                          editingSchedule?.format === format
                            ? 'border-primary-500 bg-primary-50 text-primary-700'
                            : 'border-neutral-200 hover:border-neutral-300'
                        )}
                      >
                        <Icon className="w-4 h-4" />
                        <span className="uppercase text-sm font-medium">{format}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">Recipients (one per line)</label>
                <textarea
                  ref={recipientsRef}
                  defaultValue={editingSchedule?.recipients.join('\n') || ''}
                  placeholder="email@example.com"
                  rows={4}
                  className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => {
                    setShowCreateModal(false);
                    setEditingSchedule(null);
                  }}
                  className="flex-1 px-4 py-2 border border-neutral-200 rounded-lg font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  disabled={createSchedule.isPending || updateSchedule.isPending}
                  onClick={() => {
                    const name = nameRef.current?.value || '';
                    const templateId = templateRef.current?.value || '';
                    const frequency = (frequencyRef.current?.value || 'weekly') as ScheduleFrequency;
                    const time = timeRef.current?.value || '09:00';
                    const recipients = (recipientsRef.current?.value || '').split('\n').filter(Boolean);
                    const format = (formatRef.current || 'pdf') as ReportFormat;

                    if (!name || !templateId) {
                      showError('Please fill in name and template');
                      return;
                    }

                    if (editingSchedule) {
                      updateSchedule.mutate(
                        {
                          id: Number(editingSchedule.id),
                          name,
                          recipients,
                          frequency,
                          time,
                          format,
                        },
                        {
                          onSuccess: () => {
                            success('Schedule updated');
                            setEditingSchedule(null);
                          },
                          onError: () => showError('Failed to update schedule'),
                        }
                      );
                    } else {
                      createSchedule.mutate(
                        {
                          name,
                          template_id: Number(templateId),
                          recipients,
                          frequency,
                          time,
                          format,
                          is_active: true,
                          next_scheduled: new Date().toISOString(),
                        },
                        {
                          onSuccess: () => {
                            success('Schedule created');
                            setShowCreateModal(false);
                          },
                          onError: () => showError('Failed to create schedule'),
                        }
                      );
                    }
                  }}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors disabled:opacity-50"
                >
                  {(createSchedule.isPending || updateSchedule.isPending) && <Loader2 className="w-4 h-4 animate-spin" />}
                  {editingSchedule ? 'Update Schedule' : 'Create Schedule'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
