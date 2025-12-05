import { NavLink } from 'react-router-dom';
import { useAppStore } from '@/store/useAppStore';
import {
  LayoutDashboard,
  Building2,
  Receipt,
  Briefcase,
  BarChart3,
  TrendingUp,
  Map,
  FileText,
  ChevronLeft,
  ChevronRight,
  X,
  Percent,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useEffect } from 'react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Investments', href: '/investments', icon: Building2 },
  { name: 'Transactions', href: '/transactions', icon: Receipt },
  { name: 'Deals', href: '/deals', icon: Briefcase },
  { name: 'Documents', href: '/documents', icon: FileText },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Interest Rates', href: '/interest-rates', icon: Percent },
  { name: 'Market', href: '/market', icon: TrendingUp },
  { name: 'Mapping', href: '/mapping', icon: Map },
];

export function Sidebar(){
  const { sidebarCollapsed, toggleSidebar, mobileMenuOpen, setMobileMenuOpen } = useAppStore();

  // Close mobile menu when navigating
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setMobileMenuOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [setMobileMenuOpen]);

  return (
    <>
      {/* Mobile overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          'fixed left-0 top-0 h-screen bg-neutral-800 text-white transition-all duration-300 z-50',
          // Desktop: show based on collapsed state
          'hidden lg:block',
          sidebarCollapsed ? 'lg:w-[70px]' : 'lg:w-[260px]',
          // Mobile: show/hide based on mobileMenuOpen
          mobileMenuOpen && 'block w-[280px]'
        )}
        role="navigation"
        aria-label="Main navigation"
      >
      {/* Header */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-neutral-700">
        {(!sidebarCollapsed || mobileMenuOpen) && (
          <div className="flex items-center gap-2">
            <Building2 className="w-8 h-8 text-accent-500" aria-hidden="true" />
            <span className="font-semibold text-lg">B&R Capital</span>
          </div>
        )}
        {/* Desktop toggle */}
        <button
          onClick={toggleSidebar}
          className="hidden lg:block p-2 rounded-lg hover:bg-neutral-700 transition-colors"
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="w-5 h-5" aria-hidden="true" />
          ) : (
            <ChevronLeft className="w-5 h-5" aria-hidden="true" />
          )}
        </button>
        {/* Mobile close button */}
        <button
          onClick={() => setMobileMenuOpen(false)}
          className="lg:hidden p-2 rounded-lg hover:bg-neutral-700 transition-colors"
          aria-label="Close menu"
        >
          <X className="w-5 h-5" aria-hidden="true" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="mt-6 px-3 space-y-1" aria-label="Primary">
        {navigation.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.name}
              to={item.href}
              onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors min-h-[44px]',
                  isActive
                    ? 'bg-accent-500 text-white'
                    : 'text-neutral-300 hover:bg-neutral-700 hover:text-white',
                  sidebarCollapsed && !mobileMenuOpen && 'justify-center'
                )
              }
              title={sidebarCollapsed && !mobileMenuOpen ? item.name : undefined}
              aria-label={sidebarCollapsed && !mobileMenuOpen ? item.name : undefined}
            >
              <Icon className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
              {(!sidebarCollapsed || mobileMenuOpen) && (
                <span className="font-medium">{item.name}</span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer Section */}
      {(!sidebarCollapsed || mobileMenuOpen) && (
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
    </>
  );
}
