import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import type { ImportStatus } from '../types';

interface ImportNotificationBannerProps {
  importStatus: ImportStatus | undefined;
  isLoading: boolean;
  onTriggerImport: () => void;
  isImporting: boolean;
}

export function ImportNotificationBanner({
  importStatus,
  isLoading,
  onTriggerImport,
  isImporting,
}: ImportNotificationBannerProps) {
  if (isLoading || !importStatus || importStatus.unimportedFiles.length === 0) {
    return null;
  }

  const fileCount = importStatus.unimportedFiles.length;

  return (
    <Card className="border-blue-200 bg-blue-50" role="alert">
      <CardContent className="py-3 flex items-center justify-between gap-4">
        <div className="flex items-start gap-3 min-w-0">
          <svg
            className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z"
            />
          </svg>
          <div className="min-w-0">
            <p className="text-sm font-medium text-blue-800">
              {fileCount} new sales file{fileCount > 1 ? 's' : ''} available for
              import
            </p>
            <p className="text-xs text-blue-600 truncate">
              {importStatus.unimportedFiles.join(', ')}
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={onTriggerImport}
          disabled={isImporting}
          className="flex-shrink-0 border-blue-300 text-blue-700 hover:bg-blue-100"
        >
          {isImporting ? 'Importing...' : 'Import Now'}
        </Button>
      </CardContent>
    </Card>
  );
}
