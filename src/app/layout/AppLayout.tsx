import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopNav } from './TopNav';
import { useAppStore } from '@/store/useAppStore';
import { cn } from '@/lib/utils';

export function AppLayout(){
  const { sidebarCollapsed } = useAppStore();

  return (
    <div className="min-h-screen bg-white">
      <Sidebar />
      <TopNav />

      {/* Main Content */}
      <main
        className={cn(
          'pt-16 transition-all duration-300',
          sidebarCollapsed ? 'ml-[70px]' : 'ml-[260px]'
        )}
      >
        <div className="p-6 max-w-[1920px]">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
