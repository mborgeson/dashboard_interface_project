import { Card } from '@/components/ui/card';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface KPICardProps {
  title: string;
  value: string | number;
  trend?: number;
  format?: 'currency' | 'percentage' | 'number' | 'decimal';
  description?: string;
}

export function KPICard({ title, value, trend, format = 'number', description }: KPICardProps) {
  const formatValue = (val: string | number): string => {
    if (typeof val === 'string') return val;
    
    switch (format) {
      case 'currency':
        return `$${val.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
      case 'percentage':
        return `${(val * 100).toFixed(2)}%`;
      case 'decimal':
        return val.toFixed(2);
      default:
        return val.toLocaleString('en-US');
    }
  };

  const getTrendColor = () => {
    if (!trend) return '';
    return trend > 0 ? 'text-green-600' : 'text-red-600';
  };

  const TrendIcon = trend && trend > 0 ? TrendingUp : TrendingDown;

  return (
    <Card className="p-6">
      <div className="space-y-2">
        <p className="text-sm font-medium text-neutral-600">{title}</p>
        <div className="flex items-baseline justify-between">
          <p className="text-3xl font-bold text-primary-500">{formatValue(value)}</p>
          {trend !== undefined && (
            <div className={`flex items-center gap-1 text-sm font-medium ${getTrendColor()}`}>
              <TrendIcon className="h-4 w-4" />
              <span>{Math.abs(trend).toFixed(1)}%</span>
            </div>
          )}
        </div>
        {description && (
          <p className="text-xs text-neutral-500">{description}</p>
        )}
      </div>
    </Card>
  );
}
