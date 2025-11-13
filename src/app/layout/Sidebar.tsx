import { NavLink } from 'react-router-dom';
import { useAppStore } from '@/store/useAppStore';
import {
  LayoutDashboard,
  Building2,
  BarChart3,
  Map,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Investments', href: '/investments', icon: Building2 },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Mapping', href: '/mapping', icon: Map },
];

export function Sidebar(){
  const { sidebarCollapsed, toggleSidebar } = useAppStore();

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 h-screen bg-neutral-800 text-white transition-all duration-300 z-50',
        sidebarCollapsed ? 'w-[70px]' : 'w-[260px]'
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-neutral-700">
        {!sidebarCollapsed && (
          <div className="flex items-center gap-2">
            <Building2 className="w-8 h-8 text-accent-500" />
            <span className="font-semibold text-lg">B&R Capital</span>
          </div>
        )}
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg hover:bg-neutral-700 transition-colors"
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="w-5 h-5" />
          ) : (
            <ChevronLeft className="w-5 h-5" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="mt-6 px-3 space-y-1">
        {navigation.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
                  isActive
                    ? 'bg-accent-500 text-white'
                    : 'text-neutral-300 hover:bg-neutral-700 hover:text-white',
                  sidebarCollapsed && 'justify-center'
                )
              }
              title={sidebarCollapsed ? item.name : undefined}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {!sidebarCollapsed && (
                <span className="font-medium">{item.name}</span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer Section */}
      {!sidebarCollapsed && (
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-neutral-700">
          <div className="text-xs text-neutral-400">
            <div className="font-semibold text-neutral-300 mb-1">
              Portfolio Dashboard
            </div>
            <div>12 Properties • 2,116 Units</div>
            <div className="mt-2">Phoenix MSA</div>
          </div>
        </div>
      )}
    </aside>
  );
}
