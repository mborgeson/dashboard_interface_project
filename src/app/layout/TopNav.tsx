import { useAppStore } from '@/store/useAppStore';
import { cn } from '@/lib/utils';
import { UnderwritingModal } from '@/features/underwriting';
import { GlobalSearch } from '@/features/search';

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
      <GlobalSearch />

      {/* Actions */}
      <div className="flex items-center gap-4 ml-4">
        <UnderwritingModal />

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
