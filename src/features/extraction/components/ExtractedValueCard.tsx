import { formatExtractedValue } from '../hooks/useExtraction';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Hash,
  Calendar,
  Type,
  ToggleLeft,
  AlertCircle,
  FileSpreadsheet,
  MapPin,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ExtractedValue, DataValueType } from '@/types/extraction';

interface ExtractedValueCardProps {
  value: ExtractedValue;
  compact?: boolean;
  onClick?: () => void;
  className?: string;
}

interface DataTypeConfig {
  icon: LucideIcon;
  colorClasses: string;
}

const DATA_TYPE_CONFIG: Record<DataValueType, DataTypeConfig> = {
  numeric: { icon: Hash, colorClasses: 'text-blue-600 bg-blue-50' },
  date: { icon: Calendar, colorClasses: 'text-purple-600 bg-purple-50' },
  boolean: { icon: ToggleLeft, colorClasses: 'text-amber-600 bg-amber-50' },
  error: { icon: AlertCircle, colorClasses: 'text-red-600 bg-red-50' },
  text: { icon: Type, colorClasses: 'text-neutral-600 bg-neutral-50' },
};

function DataTypeIcon({ dataType, size = 'sm' }: { dataType: DataValueType; size?: 'sm' | 'md' }) {
  const config = DATA_TYPE_CONFIG[dataType] || DATA_TYPE_CONFIG.text;
  const Icon = config.icon;
  const sizeClass = size === 'sm' ? 'h-4 w-4' : 'h-5 w-5';
  return <Icon className={sizeClass} />;
}

function getDataTypeColor(dataType: DataValueType): string {
  return (DATA_TYPE_CONFIG[dataType] || DATA_TYPE_CONFIG.text).colorClasses;
}

export function ExtractedValueCard({
  value,
  compact = false,
  onClick,
  className,
}: ExtractedValueCardProps) {
  const typeColorClasses = getDataTypeColor(value.data_type);
  const formattedValue = formatExtractedValue(value);

  if (compact) {
    return (
      <div
        className={cn(
          "flex items-center justify-between p-3 rounded-lg border transition-colors",
          value.is_error
            ? "bg-red-50 border-red-200"
            : "bg-white border-neutral-200 hover:bg-neutral-50",
          onClick && "cursor-pointer",
          className
        )}
        onClick={onClick}
      >
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <div
            className={cn(
              "flex items-center justify-center h-8 w-8 rounded-md flex-shrink-0",
              typeColorClasses
            )}
          >
            <DataTypeIcon dataType={value.data_type} size="sm" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-medium text-neutral-900 truncate">
              {value.field_name}
            </div>
            <div className="text-xs text-neutral-500">
              {value.sheet_name} - {value.cell_address}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 ml-3">
          {value.is_error ? (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-1">
                    <AlertCircle className="h-4 w-4 text-red-500" />
                    <Badge variant="destructive" className="text-xs">
                      {value.error_category || 'Error'}
                    </Badge>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{value.error_message || 'Unknown error'}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : (
            <span className="text-sm font-medium text-neutral-900 truncate max-w-[150px]">
              {formattedValue}
            </span>
          )}
        </div>
      </div>
    );
  }

  return (
    <Card
      className={cn(
        "transition-colors",
        value.is_error ? "border-red-200 bg-red-50/50" : "",
        onClick && "cursor-pointer hover:shadow-md",
        className
      )}
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3 min-w-0 flex-1">
            <div
              className={cn(
                "flex items-center justify-center h-10 w-10 rounded-lg flex-shrink-0",
                typeColorClasses
              )}
            >
              <DataTypeIcon dataType={value.data_type} size="md" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="font-medium text-neutral-900">{value.field_name}</div>
              <div className="text-sm text-neutral-500 mt-0.5">
                {value.field_category}
              </div>
            </div>
          </div>
          <Badge variant="outline" className="flex-shrink-0">
            {value.data_type}
          </Badge>
        </div>

        {/* Value Display */}
        <div className="mt-4 p-3 bg-white rounded-lg border">
          {value.is_error ? (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-2 text-red-600">
                    <AlertCircle className="h-4 w-4 flex-shrink-0" />
                    <span className="text-sm font-medium">
                      {value.error_category || 'Error'}
                    </span>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-xs">
                  <p className="text-sm">{value.error_message || 'Unknown error'}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : (
            <div className="text-lg font-semibold text-neutral-900">
              {formattedValue}
            </div>
          )}
        </div>

        {/* Location Info */}
        <div className="mt-3 flex items-center gap-4 text-xs text-neutral-500">
          <div className="flex items-center gap-1">
            <FileSpreadsheet className="h-3 w-3" />
            <span>{value.sheet_name}</span>
          </div>
          <div className="flex items-center gap-1">
            <MapPin className="h-3 w-3" />
            <span>{value.cell_address}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface ExtractedValueGridProps {
  values: ExtractedValue[];
  compact?: boolean;
  columns?: 1 | 2 | 3 | 4;
  onValueClick?: (value: ExtractedValue) => void;
  className?: string;
}

export function ExtractedValueGrid({
  values,
  compact = false,
  columns = 2,
  onValueClick,
  className,
}: ExtractedValueGridProps) {
  const gridColsClass = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 md:grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4',
  }[columns];

  if (compact) {
    return (
      <div className={cn('space-y-2', className)}>
        {values.map((value) => (
          <ExtractedValueCard
            key={value.id}
            value={value}
            compact
            onClick={onValueClick ? () => onValueClick(value) : undefined}
          />
        ))}
      </div>
    );
  }

  return (
    <div className={cn('grid gap-4', gridColsClass, className)}>
      {values.map((value) => (
        <ExtractedValueCard
          key={value.id}
          value={value}
          onClick={onValueClick ? () => onValueClick(value) : undefined}
        />
      ))}
    </div>
  );
}
