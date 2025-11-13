import { Search, Calculator } from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

export function TopNav(){
  const { sidebarCollapsed } = useAppStore();

  return (
    <header
      className={cn(
        'fixed top-0 right-0 h-16 bg-white border-b border-neutral-200 flex items-center justify-between px-6 transition-all duration-300 z-40',
        sidebarCollapsed ? 'left-[70px]' : 'left-[260px]'
      )}
    >
      {/* Search */}
      <div className="flex-1 max-w-2xl">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
          <input
            type="text"
            placeholder="Search properties, transactions..."
            className="w-full pl-10 pr-4 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-4 ml-4">
        <Button
          variant="default"
          size="sm"
          className="bg-accent-500 hover:bg-accent-600"
        >
          <Calculator className="w-4 h-4 mr-2" />
          Underwrite Deal
        </Button>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-sm font-medium text-neutral-900">
              Portfolio Manager
            </div>
            <div className="text-xs text-neutral-500">B&R Capital</div>
          </div>
          <div className="w-10 h-10 rounded-full bg-primary-500 text-white flex items-center justify-center font-semibold">
            BR
          </div>
        </div>
      </div>
    </header>
  );
}
