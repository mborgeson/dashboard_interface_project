import { FileX, Inbox, Search, Plus, FolderOpen, BarChart3, Home } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
    variant?: 'default' | 'outline' | 'secondary';
  };
  className?: string;
  iconClassName?: string;
}

export function EmptyState({
  icon: Icon = FileX,
  title,
  description,
  action,
  className,
  iconClassName,
}: EmptyStateProps) {
  return (
    <Card className={cn('border-dashed', className)}>
      <CardContent className="flex flex-col items-center justify-center text-center p-12">
        <div className={cn(
          'rounded-full bg-muted p-4 mb-4',
          iconClassName
        )}>
          <Icon className="h-8 w-8 text-muted-foreground" />
        </div>
        
        <h3 className="font-semibold text-lg mb-2">{title}</h3>
        
        {description && (
          <p className="text-sm text-muted-foreground mb-6 max-w-sm">
            {description}
          </p>
        )}
        
        {action && (
          <Button
            onClick={action.onClick}
            variant={action.variant || 'default'}
            className="gap-2"
          >
            <Plus className="h-4 w-4" />
            {action.label}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

interface CompactEmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  className?: string;
}

export function CompactEmptyState({
  icon: Icon = Inbox,
  title,
  description,
  className,
}: CompactEmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center p-8 text-center', className)}>
      <Icon className="h-12 w-12 text-muted-foreground/60 mb-3" />
      <h4 className="font-medium text-sm mb-1">{title}</h4>
      {description && (
        <p className="text-xs text-muted-foreground max-w-xs">
          {description}
        </p>
      )}
    </div>
  );
}

interface TableEmptyStateProps {
  searchTerm?: string;
  onClearSearch?: () => void;
  className?: string;
}

export function TableEmptyState({
  searchTerm,
  onClearSearch,
  className,
}: TableEmptyStateProps) {
  const hasSearch = searchTerm && searchTerm.length > 0;

  return (
    <div className={cn(
      'flex flex-col items-center justify-center p-12 text-center border-t',
      className
    )}>
      <Search className="h-12 w-12 text-muted-foreground/60 mb-3" />
      <h4 className="font-medium text-base mb-2">
        {hasSearch ? 'No results found' : 'No data available'}
      </h4>
      <p className="text-sm text-muted-foreground mb-4 max-w-sm">
        {hasSearch
          ? `No items match "${searchTerm}". Try adjusting your search.`
          : 'There are no items to display at this time.'}
      </p>
      {hasSearch && onClearSearch && (
        <Button onClick={onClearSearch} variant="outline" size="sm">
          Clear Search
        </Button>
      )}
    </div>
  );
}

// Preset empty states for common scenarios
export function EmptyInvestments({ onAdd }: { onAdd?: () => void }) {
  return (
    <EmptyState
      icon={Home}
      title="No properties yet"
      description="Start building your real estate portfolio by adding your first property investment."
      action={onAdd ? {
        label: 'Add Property',
        onClick: onAdd,
      } : undefined}
    />
  );
}

export function EmptyTransactions() {
  return (
    <EmptyState
      icon={BarChart3}
      title="No transactions"
      description="Transaction history will appear here once you record financial activities."
    />
  );
}

export function EmptyDocuments({ onUpload }: { onUpload?: () => void }) {
  return (
    <EmptyState
      icon={FolderOpen}
      title="No documents"
      description="Upload important documents like contracts, reports, and agreements to keep them organized."
      action={onUpload ? {
        label: 'Upload Document',
        onClick: onUpload,
        variant: 'outline',
      } : undefined}
    />
  );
}

export function EmptyDeals({ onAdd }: { onAdd?: () => void }) {
  return (
    <EmptyState
      icon={Inbox}
      title="No deals in pipeline"
      description="Track potential investment opportunities by adding them to your deal pipeline."
      action={onAdd ? {
        label: 'Add Deal',
        onClick: onAdd,
      } : undefined}
    />
  );
}
