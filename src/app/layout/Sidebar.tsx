import { useAppStore } from '@/store/useAppStore';
import { useProperties, selectProperties } from '@/hooks/api';
import { PrefetchLink } from '@/components/PrefetchLink';
import {
  LayoutDashboard,
  Building2,
  Briefcase,
  BarChart3,
  TrendingUp,
  Map,
  FileText,
  ChevronLeft,
  ChevronRight,
  X,
  Percent,
  ClipboardList,
  ExternalLink,
  Globe,
  FolderOpen,
  Linkedin,
  Calculator,
  FileSpreadsheet,
  Search,
  Database,
  HardHat,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useEffect, useMemo } from 'react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Investments', href: '/investments', icon: Building2 },
  { name: 'Deals', href: '/deals', icon: Briefcase },
  { name: 'Documents', href: '/documents', icon: FileText },
  { name: 'UW Extraction', href: '/extraction', icon: Database },
  { name: 'Reporting', href: '/reporting', icon: ClipboardList },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Interest Rates', href: '/interest-rates', icon: Percent },
  { name: 'Market', href: '/market', icon: TrendingUp },
  { name: 'Sales Analysis', href: '/sales-analysis', icon: FileSpreadsheet },
  { name: 'Construction', href: '/construction-pipeline', icon: HardHat },
  { name: 'Mapping', href: '/mapping', icon: Map },
];

const externalLinks = [
  { name: 'B&R Capital', href: 'https://www.bandrcapital.com/', icon: Globe },
  { name: 'SharePoint', href: 'https://bandrcapital.sharepoint.com/sites/BRCapital-Internal/Real%20Estate/Forms/AllItems.aspx', icon: FolderOpen },
  { name: 'LinkedIn', href: 'https://www.linkedin.com/company/b-r-capital/', icon: Linkedin },
];

const externalTools = [
  { name: 'Rent Roll Analyzer', href: 'https://rent-roll-processor.onrender.com/', icon: FileSpreadsheet },
  { name: 'T12 Analyzer', href: '#', icon: Calculator, disabled: true },
  { name: 'Rent Scraper', href: '#', icon: Search, disabled: true },
];

export function Sidebar(){
  const { sidebarCollapsed, toggleSidebar, mobileMenuOpen, setMobileMenuOpen } = useAppStore();

  // Fetch properties from API
  const { data } = useProperties();
  const properties = selectProperties(data);

  // Compute portfolio stats from API data
  const portfolioStats = useMemo(() => {
    const totalProperties = properties.length;
    const totalUnits = properties.reduce((sum, p) => sum + p.propertyDetails.units, 0);
    return { totalProperties, totalUnits };
  }, [properties]);

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
            <PrefetchLink
              key={item.name}
              to={item.href}
              onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors min-h-[44px]',
                  isActive
                    ? 'bg-accent-600 text-white'
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
            </PrefetchLink>
          );
        })}
      </nav>

      {/* External Links Section */}
      {(!sidebarCollapsed || mobileMenuOpen) && (
        <div className="mt-6 px-3">
          <div className="text-xs font-semibold text-neutral-500 uppercase tracking-wider px-3 mb-2">
            External
          </div>
          <div className="space-y-1">
            {externalLinks.map((link) => {
              const Icon = link.icon;
              return (
                <a
                  key={link.name}
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 px-3 py-2 rounded-lg text-neutral-400 hover:bg-neutral-700 hover:text-white transition-colors min-h-[40px]"
                >
                  <Icon className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                  <span className="text-sm">{link.name}</span>
                  <ExternalLink className="w-3 h-3 ml-auto opacity-50" aria-hidden="true" />
                </a>
              );
            })}
          </div>
        </div>
      )}

      {/* External Tools Section */}
      {(!sidebarCollapsed || mobileMenuOpen) && (
        <div className="mt-4 px-3">
          <div className="text-xs font-semibold text-neutral-500 uppercase tracking-wider px-3 mb-2">
            Tools
          </div>
          <div className="space-y-1">
            {externalTools.map((tool) => {
              const Icon = tool.icon;
              const isDisabled = 'disabled' in tool && tool.disabled;
              return (
                <a
                  key={tool.name}
                  href={isDisabled ? undefined : tool.href}
                  target={isDisabled ? undefined : '_blank'}
                  rel={isDisabled ? undefined : 'noopener noreferrer'}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors min-h-[40px]',
                    isDisabled
                      ? 'text-neutral-600 cursor-not-allowed'
                      : 'text-neutral-400 hover:bg-neutral-700 hover:text-white'
                  )}
                  title={isDisabled ? 'Coming soon' : undefined}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                  <span className="text-sm">{tool.name}</span>
                  {isDisabled ? (
                    <span className="ml-auto text-[10px] text-neutral-600 bg-neutral-700/50 px-1.5 py-0.5 rounded">Soon</span>
                  ) : (
                    <ExternalLink className="w-3 h-3 ml-auto opacity-50" aria-hidden="true" />
                  )}
                </a>
              );
            })}
          </div>
        </div>
      )}

      {/* Footer Section */}
      {(!sidebarCollapsed || mobileMenuOpen) && (
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-neutral-700">
          <div className="text-xs text-neutral-400">
            <div>Portfolio Dashboard</div>
            <div>{portfolioStats.totalProperties} Properties • {portfolioStats.totalUnits.toLocaleString()} Units</div>
            <div className="mt-2">Phoenix MSA</div>
          </div>
        </div>
      )}
    </aside>
    </>
  );
}
