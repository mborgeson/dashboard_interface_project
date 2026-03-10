/**
 * ActivityItem - Single activity item in the timeline
 */
import {
  ArrowRight,
  FileText,
  File,
  Phone,
  Mail,
  Calendar,
  MoreHorizontal,
  User,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { DealActivity } from '@/hooks/api/useDeals';
import { cn } from '@/lib/utils';
import { formatRelativeTime, formatTime } from '@/lib/dateUtils';

interface ActivityItemProps {
  activity: DealActivity;
  /** Reserved for future use when rendering first item differently */
  isFirst?: boolean;
  isLast?: boolean;
}

type ActivityType = DealActivity['type'];

interface ActivityTypeConfig {
  icon: LucideIcon;
  bgColor: string;
  textColor: string;
  label: string;
}

const ACTIVITY_TYPE_CONFIG: Record<ActivityType, ActivityTypeConfig> = {
  stage_change: {
    icon: ArrowRight,
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-600',
    label: 'Stage Change',
  },
  note: {
    icon: FileText,
    bgColor: 'bg-neutral-100',
    textColor: 'text-neutral-600',
    label: 'Note',
  },
  document: {
    icon: File,
    bgColor: 'bg-purple-100',
    textColor: 'text-purple-600',
    label: 'Document',
  },
  call: {
    icon: Phone,
    bgColor: 'bg-green-100',
    textColor: 'text-green-600',
    label: 'Call',
  },
  email: {
    icon: Mail,
    bgColor: 'bg-amber-100',
    textColor: 'text-amber-600',
    label: 'Email',
  },
  meeting: {
    icon: Calendar,
    bgColor: 'bg-red-100',
    textColor: 'text-red-600',
    label: 'Meeting',
  },
  other: {
    icon: MoreHorizontal,
    bgColor: 'bg-neutral-100',
    textColor: 'text-neutral-600',
    label: 'Other',
  },
};

export function ActivityItem({ activity, isLast }: ActivityItemProps) {
  const config = ACTIVITY_TYPE_CONFIG[activity.type];
  const Icon = config.icon;

  return (
    <div className="flex gap-3 relative">
      {/* Timeline Line */}
      {!isLast && (
        <div className="absolute left-5 top-10 w-0.5 h-full -translate-x-1/2 bg-neutral-200" />
      )}

      {/* Icon */}
      <div
        className={cn(
          'flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center relative z-10',
          config.bgColor
        )}
      >
        <Icon className={cn('w-5 h-5', config.textColor)} />
      </div>

      {/* Content */}
      <div className={cn('flex-1 pb-4', isLast && 'pb-0')}>
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className={cn('text-xs font-semibold uppercase tracking-wide', config.textColor)}>
                {config.label}
              </span>
              <span className="text-xs text-neutral-400">•</span>
              <span className="text-xs text-neutral-500">{formatRelativeTime(activity.timestamp)}</span>
            </div>
            <p className="text-sm text-neutral-900">{activity.description}</p>
          </div>
          <span className="text-xs text-neutral-400 flex-shrink-0 ml-2">
            {formatTime(activity.timestamp)}
          </span>
        </div>

        {/* User */}
        <div className="flex items-center gap-1.5 mt-2 text-xs text-neutral-500">
          <User className="w-3.5 h-3.5" />
          <span>{activity.user}</span>
        </div>

        {/* Metadata (if any) */}
        {activity.metadata && Object.keys(activity.metadata).length > 0 && (
          <div className="mt-2 p-2 bg-neutral-50 rounded-md text-xs text-neutral-600">
            {Object.entries(activity.metadata).map(([key, value]) => (
              <div key={key} className="flex gap-2">
                <span className="font-medium capitalize">{key.replace(/_/g, ' ')}:</span>
                <span>{String(value)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
