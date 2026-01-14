/**
 * PropertyActivityItem - Single activity item in the property activity timeline
 */
import {
  Eye,
  Edit3,
  MessageSquare,
  RefreshCw,
  Upload,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { PropertyActivity, PropertyActivityType } from '@/hooks/api/usePropertyActivities';
import { cn } from '@/lib/utils';

interface PropertyActivityItemProps {
  activity: PropertyActivity;
  /** Reserved for future use - e.g., first item styling */
  isFirst?: boolean;
  isLast?: boolean;
}

interface ActivityTypeConfig {
  icon: LucideIcon;
  bgColor: string;
  textColor: string;
  label: string;
}

const ACTIVITY_TYPE_CONFIG: Record<PropertyActivityType, ActivityTypeConfig> = {
  view: {
    icon: Eye,
    bgColor: 'bg-slate-100',
    textColor: 'text-slate-600',
    label: 'Viewed',
  },
  edit: {
    icon: Edit3,
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-600',
    label: 'Edited',
  },
  comment: {
    icon: MessageSquare,
    bgColor: 'bg-green-100',
    textColor: 'text-green-600',
    label: 'Comment',
  },
  status_change: {
    icon: RefreshCw,
    bgColor: 'bg-amber-100',
    textColor: 'text-amber-600',
    label: 'Status Change',
  },
  document_upload: {
    icon: Upload,
    bgColor: 'bg-purple-100',
    textColor: 'text-purple-600',
    label: 'Document',
  },
};

function formatTimeAgo(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) {
    return 'just now';
  }
  if (diffMins < 60) {
    return `${diffMins} minute${diffMins === 1 ? '' : 's'} ago`;
  }
  if (diffHours < 24) {
    return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
  }
  if (diffDays < 7) {
    return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
  }

  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined,
  });
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

export function PropertyActivityItem({ activity, isLast }: PropertyActivityItemProps) {
  const config = ACTIVITY_TYPE_CONFIG[activity.type];
  const Icon = config.icon;

  return (
    <div className="flex gap-3 relative">
      {/* Timeline Line */}
      {!isLast && (
        <div className="absolute left-5 top-12 w-0.5 h-[calc(100%-12px)] -translate-x-1/2 bg-neutral-200" />
      )}

      {/* User Avatar */}
      <div className="flex-shrink-0 w-10 h-10 rounded-full bg-neutral-200 flex items-center justify-center relative z-10 text-sm font-medium text-neutral-600">
        {activity.userAvatar ? (
          <img
            src={activity.userAvatar}
            alt={activity.userName}
            className="w-full h-full rounded-full object-cover"
          />
        ) : (
          getInitials(activity.userName)
        )}
      </div>

      {/* Content */}
      <div className={cn('flex-1 pb-4', isLast && 'pb-0')}>
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-center flex-wrap gap-2 mb-1">
              <span className="font-medium text-sm text-neutral-900">{activity.userName}</span>
              <div
                className={cn(
                  'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
                  config.bgColor,
                  config.textColor
                )}
              >
                <Icon className="w-3 h-3" />
                {config.label}
              </div>
              <span className="text-xs text-neutral-400">{formatTimeAgo(activity.timestamp)}</span>
            </div>

            {/* Description */}
            <p className="text-sm text-neutral-700">{activity.description}</p>

            {/* Metadata (if any) */}
            {activity.metadata && Object.keys(activity.metadata).length > 0 && (
              <div className="mt-2 p-2 bg-neutral-50 rounded-md text-xs text-neutral-600 inline-block">
                {Object.entries(activity.metadata).map(([key, value]) => (
                  <div key={key} className="flex gap-2">
                    <span className="font-medium capitalize">{key.replace(/_/g, ' ')}:</span>
                    <span className="text-neutral-500">{String(value)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Time */}
          <span className="text-xs text-neutral-400 flex-shrink-0 whitespace-nowrap">
            {formatTime(activity.timestamp)}
          </span>
        </div>
      </div>
    </div>
  );
}
