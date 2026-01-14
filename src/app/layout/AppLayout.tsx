import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopNav } from './TopNav';
import { useAppStore } from '@/store/useAppStore';
import { cn } from '@/lib/utils';
import { ComparisonBar } from '@/components/comparison';

export function AppLayout(){
  const { sidebarCollapsed } = useAppStore();

  return (
    <div className="min-h-screen bg-white">
      {/* Skip to main content link for keyboard users */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2 focus:bg-primary-500 focus:text-white focus:rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-600"
      >
        Skip to main content
      </a>
      <Sidebar />
      <TopNav />

      {/* Main Content */}
      <main
        id="main-content"
        className={cn(
          'pt-16 transition-all duration-300',
          // Mobile: no margin (full width), Desktop: adjust for sidebar
          'ml-0 lg:ml-[260px]',
          sidebarCollapsed && 'lg:ml-[70px]'
        )}
        role="main"
        aria-label="Main content"
      >
        <div className="p-4 md:p-6 max-w-[1920px]">
          <Outlet />
        </div>
      </main>

      {/* Floating comparison bar */}
      <ComparisonBar />
    </div>
  );
}
