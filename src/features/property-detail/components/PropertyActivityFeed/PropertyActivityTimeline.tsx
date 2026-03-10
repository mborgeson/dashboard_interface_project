/**
 * PropertyActivityTimeline - Timeline view of property activities grouped by date
 */
import { useMemo } from 'react';
import type { PropertyActivity } from '@/hooks/api/usePropertyActivities';
import { getDateGroupLabel } from '@/lib/dateUtils';
import { PropertyActivityItem } from './PropertyActivityItem';

interface PropertyActivityTimelineProps {
  activities: PropertyActivity[];
  groupByDate?: boolean;
}

export function PropertyActivityTimeline({
  activities,
  groupByDate = true,
}: PropertyActivityTimelineProps) {
  const groupedActivities = useMemo(() => {
    if (!groupByDate) {
      return [{ group: null, activities }];
    }

    const groups: { group: string; activities: PropertyActivity[] }[] = [];
    let currentGroup: string | null = null;
    let currentActivities: PropertyActivity[] = [];

    for (const activity of activities) {
      const group = getDateGroupLabel(activity.timestamp);
      if (group !== currentGroup) {
        if (currentGroup !== null) {
          groups.push({ group: currentGroup, activities: currentActivities });
        }
        currentGroup = group;
        currentActivities = [activity];
      } else {
        currentActivities.push(activity);
      }
    }

    if (currentGroup !== null) {
      groups.push({ group: currentGroup, activities: currentActivities });
    }

    return groups;
  }, [activities, groupByDate]);

  return (
    <div className="space-y-6">
      {groupedActivities.map((group, groupIndex) => (
        <div key={group.group || groupIndex}>
          {group.group && (
            <div className="flex items-center gap-4 mb-4">
              <span className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                {group.group}
              </span>
              <div className="flex-1 h-px bg-neutral-200" />
            </div>
          )}
          <div className="space-y-0">
            {group.activities.map((activity, index) => (
              <PropertyActivityItem
                key={activity.id}
                activity={activity}
                isFirst={index === 0}
                isLast={index === group.activities.length - 1}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
