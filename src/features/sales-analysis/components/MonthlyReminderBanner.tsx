import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import type { ReminderStatus } from '../types';

interface MonthlyReminderBannerProps {
  reminderStatus: ReminderStatus | undefined;
  isLoading: boolean;
  onDismiss: () => void;
}

export function MonthlyReminderBanner({
  reminderStatus,
  isLoading,
  onDismiss,
}: MonthlyReminderBannerProps) {
  if (isLoading || !reminderStatus || !reminderStatus.showReminder) {
    return null;
  }

  return (
    <Card className="border-amber-200 bg-amber-50" role="alert">
      <CardContent className="py-3 flex items-center justify-between gap-4">
        <div className="flex items-start gap-3 min-w-0">
          <svg
            className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
            />
          </svg>
          <div className="min-w-0">
            <p className="text-sm font-medium text-amber-800">
              Monthly reminder: Check for new CoStar sales data
            </p>
            <p className="text-xs text-amber-600">
              {reminderStatus.lastImportedFileName
                ? `Last imported: ${reminderStatus.lastImportedFileName}`
                : 'No files imported yet'}
              {reminderStatus.lastImportedFileDate &&
                ` (${reminderStatus.lastImportedFileDate})`}
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={onDismiss}
          className="flex-shrink-0 border-amber-300 text-amber-700 hover:bg-amber-100"
        >
          Dismiss
        </Button>
      </CardContent>
    </Card>
  );
}
