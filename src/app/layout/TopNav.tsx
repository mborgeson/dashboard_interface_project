import { useAppStore } from '@/store/useAppStore';
import { cn } from '@/lib/utils';
import { UnderwritingModal } from '@/features/underwriting';
import { GlobalSearch } from '@/components/GlobalSearch';
import { useSearchStore } from '@/stores/searchStore';
import { useToast } from '@/hooks/useToast';
import { Search, Command, Bell, Menu } from 'lucide-react';

export function TopNav(){
  const { sidebarCollapsed, toggleMobileMenu } = useAppStore();
  const { setOpen } = useSearchStore();
  const { success, error, warning, info } = useToast();

  const handleToastDemo = () => {
    // Demo all toast types in sequence
    success('Success notification', { description: 'This is a success message' });
    setTimeout(() => {
      info('Info notification', { description: 'This is an informational message' });
    }, 500);
    setTimeout(() => {
      warning('Warning notification', { description: 'This is a warning message' });
    }, 1000);
    setTimeout(() => {
      error('Error notification', { description: 'This is an error message' });
    }, 1500);
  };

  return (
    <header
      className={cn(
        'fixed top-0 right-0 h-16 bg-white border-b border-neutral-200 flex items-center justify-between px-4 md:px-6 transition-all duration-300 z-40',
        // Desktop: adjust for sidebar width
        'left-0 lg:left-[260px]',
        sidebarCollapsed && 'lg:left-[70px]'
      )}
      role="banner"
    >
      {/* Mobile menu button */}
      <button
        onClick={toggleMobileMenu}
        className="lg:hidden p-2 rounded-lg hover:bg-neutral-100 transition-colors mr-2"
        aria-label="Open navigation menu"
      >
        <Menu className="w-6 h-6 text-neutral-600" aria-hidden="true" />
      </button>

      {/* Search Trigger */}
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 px-4 py-2 border border-neutral-300 rounded-lg hover:bg-neutral-50 transition-colors text-neutral-600 hover:text-neutral-900"
        aria-label="Open search (Ctrl+K)"
        aria-haspopup="dialog"
      >
        <Search className="w-4 h-4" aria-hidden="true" />
        <span className="text-sm">Search...</span>
        <div className="ml-4 flex items-center gap-1 text-xs text-neutral-400" aria-hidden="true">
          <Command className="w-3 h-3" />
          <span>K</span>
        </div>
      </button>

      {/* Global Search Modal */}
      <GlobalSearch />

      {/* Actions */}
      <div className="flex items-center gap-4 ml-4">
        <button
          onClick={handleToastDemo}
          className="flex items-center gap-2 px-3 py-2 border border-neutral-300 rounded-lg hover:bg-neutral-50 transition-colors text-neutral-600 hover:text-neutral-900"
          title="Test Toast Notifications"
          aria-label="Show toast notification demo"
        >
          <Bell className="w-4 h-4" aria-hidden="true" />
          <span className="text-sm">Toast Demo</span>
        </button>

        <UnderwritingModal />

        <div className="flex items-center gap-3" role="status" aria-label="Current user">
          <div className="text-right">
            <div className="text-sm font-medium text-neutral-900">
              Portfolio Manager
            </div>
            <div className="text-xs text-neutral-500">B&R Capital</div>
          </div>
          <div
            className="w-10 h-10 rounded-full bg-primary-500 text-white flex items-center justify-center font-semibold"
            role="img"
            aria-label="User avatar for Portfolio Manager"
          >
            BR
          </div>
        </div>
      </div>
    </header>
  );
}
