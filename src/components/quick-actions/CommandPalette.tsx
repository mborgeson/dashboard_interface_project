import { useCallback, useEffect, useState } from 'react';
import { Command } from 'cmdk';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  LayoutDashboard,
  FileBarChart,
  Building2,
  TrendingUp,
  Plus,
  FileText,
  GitCompare,
  Map,
  DollarSign,
  Settings,
  HelpCircle,
  Clock,
  Command as CommandIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useQuickActions } from '@/contexts/QuickActionsContext';
import { Dialog, DialogContent } from '@/components/ui/dialog';

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon: React.ReactNode;
  shortcut?: string;
  action: () => void;
  group: 'navigation' | 'actions' | 'search' | 'recent';
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const navigate = useNavigate();
  const { recentActions, openShortcutsHelp, toggleCompareMode } = useQuickActions();
  const [search, setSearch] = useState('');

  // Reset search when palette opens
  useEffect(() => {
    if (open) {
      setSearch('');
    }
  }, [open]);

  const handleSelect = useCallback(
    (callback: () => void) => {
      callback();
      onOpenChange(false);
    },
    [onOpenChange]
  );

  // Navigation commands
  const navigationCommands: CommandItem[] = [
    {
      id: 'nav-dashboard',
      label: 'Go to Dashboard',
      description: 'View main dashboard',
      icon: <LayoutDashboard className="w-4 h-4" />,
      shortcut: 'G D',
      action: () => navigate('/'),
      group: 'navigation',
    },
    {
      id: 'nav-deals',
      label: 'Go to Deals',
      description: 'View deal pipeline',
      icon: <FileBarChart className="w-4 h-4" />,
      shortcut: 'G L',
      action: () => navigate('/deals'),
      group: 'navigation',
    },
    {
      id: 'nav-investments',
      label: 'Go to Investments',
      description: 'View investment portfolio',
      icon: <Building2 className="w-4 h-4" />,
      action: () => navigate('/investments'),
      group: 'navigation',
    },
    {
      id: 'nav-analytics',
      label: 'Go to Analytics',
      description: 'View analytics and reports',
      icon: <TrendingUp className="w-4 h-4" />,
      action: () => navigate('/analytics'),
      group: 'navigation',
    },
    {
      id: 'nav-mapping',
      label: 'Go to Mapping',
      description: 'View property map',
      icon: <Map className="w-4 h-4" />,
      action: () => navigate('/mapping'),
      group: 'navigation',
    },
    {
      id: 'nav-transactions',
      label: 'Go to Transactions',
      description: 'View transactions',
      icon: <DollarSign className="w-4 h-4" />,
      action: () => navigate('/transactions'),
      group: 'navigation',
    },
    {
      id: 'nav-reporting',
      label: 'Go to Reporting',
      description: 'View reporting suite',
      icon: <FileText className="w-4 h-4" />,
      action: () => navigate('/reporting'),
      group: 'navigation',
    },
  ];

  // Action commands
  const actionCommands: CommandItem[] = [
    {
      id: 'action-add-deal',
      label: 'Add New Deal',
      description: 'Create a new deal',
      icon: <Plus className="w-4 h-4" />,
      action: () => {
        navigate('/deals');
        // Could trigger modal opening via context
      },
      group: 'actions',
    },
    {
      id: 'action-generate-report',
      label: 'Generate Report',
      description: 'Create a new report',
      icon: <FileText className="w-4 h-4" />,
      action: () => navigate('/reporting'),
      group: 'actions',
    },
    {
      id: 'action-compare-deals',
      label: 'Compare Deals',
      description: 'Enter deal comparison mode',
      icon: <GitCompare className="w-4 h-4" />,
      shortcut: 'Ctrl+Shift+C',
      action: () => {
        toggleCompareMode();
        navigate('/deals');
      },
      group: 'actions',
    },
    {
      id: 'action-shortcuts',
      label: 'Keyboard Shortcuts',
      description: 'View all shortcuts',
      icon: <HelpCircle className="w-4 h-4" />,
      shortcut: '?',
      action: () => openShortcutsHelp(),
      group: 'actions',
    },
  ];

  // Search commands
  const searchCommands: CommandItem[] = [
    {
      id: 'search-deals',
      label: 'Search Deals',
      description: 'Find deals by name or property',
      icon: <Search className="w-4 h-4" />,
      action: () => navigate('/deals?search=true'),
      group: 'search',
    },
    {
      id: 'search-properties',
      label: 'Search Properties',
      description: 'Find properties',
      icon: <Building2 className="w-4 h-4" />,
      action: () => navigate('/investments?search=true'),
      group: 'search',
    },
  ];

  // Recent actions as commands
  const recentCommands: CommandItem[] = recentActions.slice(0, 5).map((action, index) => ({
    id: `recent-${action.id}`,
    label: action.label,
    description: `${new Date(action.timestamp).toLocaleTimeString()}`,
    icon: <Clock className="w-4 h-4" />,
    action: () => {
      // Re-execute or navigate to the action - placeholder for future implementation
    },
    group: 'recent' as const,
  }));

  const allCommands = [
    ...navigationCommands,
    ...actionCommands,
    ...searchCommands,
    ...(recentCommands.length > 0 ? recentCommands : []),
  ];

  const groupLabels: Record<CommandItem['group'], string> = {
    navigation: 'Navigation',
    actions: 'Actions',
    search: 'Search',
    recent: 'Recent',
  };

  const groups = ['navigation', 'actions', 'search', 'recent'] as const;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="p-0 overflow-hidden max-w-[640px] shadow-2xl">
        <Command
          className="rounded-lg border-0"
          filter={(value, search) => {
            const item = allCommands.find((cmd) => cmd.id === value);
            if (!item) return 0;
            const searchLower = search.toLowerCase();
            if (item.label.toLowerCase().includes(searchLower)) return 1;
            if (item.description?.toLowerCase().includes(searchLower)) return 0.5;
            return 0;
          }}
        >
          <div className="flex items-center border-b px-3">
            <CommandIcon className="mr-2 h-4 w-4 shrink-0 opacity-50" />
            <Command.Input
              value={search}
              onValueChange={setSearch}
              placeholder="Type a command or search..."
              className="flex h-12 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-neutral-500 disabled:cursor-not-allowed disabled:opacity-50"
            />
            <kbd className="ml-2 pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-neutral-100 px-1.5 font-mono text-[10px] font-medium text-neutral-600">
              ESC
            </kbd>
          </div>
          <Command.List className="max-h-[400px] overflow-y-auto p-2">
            <Command.Empty className="py-6 text-center text-sm text-neutral-500">
              No results found.
            </Command.Empty>

            {groups.map((group) => {
              const groupCommands = allCommands.filter((cmd) => cmd.group === group);
              if (groupCommands.length === 0) return null;

              return (
                <Command.Group key={group} heading={groupLabels[group]}>
                  {groupCommands.map((command) => (
                    <Command.Item
                      key={command.id}
                      value={command.id}
                      onSelect={() => handleSelect(command.action)}
                      className={cn(
                        'relative flex cursor-pointer select-none items-center rounded-md px-2 py-2.5 text-sm outline-none',
                        'hover:bg-neutral-100 data-[selected=true]:bg-neutral-100',
                        'aria-selected:bg-neutral-100'
                      )}
                    >
                      <span className="mr-3 flex h-8 w-8 items-center justify-center rounded-md border bg-neutral-50">
                        {command.icon}
                      </span>
                      <div className="flex flex-1 flex-col">
                        <span className="font-medium">{command.label}</span>
                        {command.description && (
                          <span className="text-xs text-neutral-500">
                            {command.description}
                          </span>
                        )}
                      </div>
                      {command.shortcut && (
                        <kbd className="ml-auto pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-neutral-100 px-1.5 font-mono text-[10px] font-medium text-neutral-600">
                          {command.shortcut}
                        </kbd>
                      )}
                    </Command.Item>
                  ))}
                </Command.Group>
              );
            })}
          </Command.List>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
