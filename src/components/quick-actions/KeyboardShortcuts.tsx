import { useEffect, useRef, useCallback, type ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useQuickActions } from '@/contexts/QuickActionsContext';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { cn } from '@/lib/utils';

interface KeyboardShortcutsProviderProps {
  children: ReactNode;
}

interface ShortcutGroup {
  title: string;
  shortcuts: {
    keys: string[];
    description: string;
  }[];
}

const shortcutGroups: ShortcutGroup[] = [
  {
    title: 'General',
    shortcuts: [
      { keys: ['Ctrl', 'K'], description: 'Open command palette' },
      { keys: ['?'], description: 'Show keyboard shortcuts' },
      { keys: ['Esc'], description: 'Close dialogs / Cancel' },
    ],
  },
  {
    title: 'Navigation',
    shortcuts: [
      { keys: ['G', 'D'], description: 'Go to Dashboard' },
      { keys: ['G', 'L'], description: 'Go to Deals List' },
      { keys: ['G', 'A'], description: 'Go to Analytics' },
      { keys: ['G', 'M'], description: 'Go to Mapping' },
      { keys: ['G', 'I'], description: 'Go to Investments' },
      { keys: ['G', 'T'], description: 'Go to Transactions' },
      { keys: ['G', 'R'], description: 'Go to Reporting' },
    ],
  },
  {
    title: 'Actions',
    shortcuts: [
      { keys: ['Ctrl', 'W'], description: 'Toggle watchlist (on deal)' },
      { keys: ['Ctrl', 'Shift', 'C'], description: 'Toggle compare mode' },
      { keys: ['Ctrl', 'S'], description: 'Save (in forms)' },
      { keys: ['Ctrl', 'E'], description: 'Export current view' },
    ],
  },
];

// Detect if running on Mac
const isMac = typeof navigator !== 'undefined' && /Mac|iPod|iPhone|iPad/.test(navigator.platform);
const modKey = isMac ? 'Cmd' : 'Ctrl';

export function KeyboardShortcutsProvider({ children }: KeyboardShortcutsProviderProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    toggleCommandPalette,
    openShortcutsHelp,
    closeShortcutsHelp,
    shortcutsHelpOpen,
    toggleWatchlist,
    toggleCompareMode,
  } = useQuickActions();

  // Track pending 'g' key for two-key shortcuts
  const pendingGKey = useRef(false);
  const gKeyTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clear g key after timeout
  const clearGKey = useCallback(() => {
    pendingGKey.current = false;
    if (gKeyTimeout.current) {
      clearTimeout(gKeyTimeout.current);
    }
  }, []);

  // Handle keyboard events
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in inputs
      const target = event.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return;
      }

      const key = event.key.toLowerCase();
      const isCtrlOrCmd = isMac ? event.metaKey : event.ctrlKey;
      const isShift = event.shiftKey;

      // Command palette: Ctrl/Cmd + K
      if (isCtrlOrCmd && key === 'k') {
        event.preventDefault();
        toggleCommandPalette();
        return;
      }

      // Shortcuts help: ?
      if (key === '?' && !isCtrlOrCmd) {
        event.preventDefault();
        openShortcutsHelp();
        return;
      }

      // Toggle watchlist: Ctrl/Cmd + W (on deal pages)
      if (isCtrlOrCmd && key === 'w' && !isShift) {
        // Get deal ID from URL if on deal detail page
        const dealMatch = location.pathname.match(/\/deals\/([^/]+)/);
        if (dealMatch) {
          event.preventDefault();
          toggleWatchlist(dealMatch[1]);
          return;
        }
      }

      // Toggle compare mode: Ctrl/Cmd + Shift + C
      if (isCtrlOrCmd && isShift && key === 'c') {
        event.preventDefault();
        toggleCompareMode();
        return;
      }

      // Two-key navigation shortcuts: G then [key]
      if (key === 'g' && !isCtrlOrCmd && !isShift) {
        pendingGKey.current = true;
        // Clear after 1 second
        gKeyTimeout.current = setTimeout(clearGKey, 1000);
        return;
      }

      // Handle second key of g-sequence
      if (pendingGKey.current && !isCtrlOrCmd && !isShift) {
        clearGKey();

        switch (key) {
          case 'd':
            event.preventDefault();
            navigate('/');
            break;
          case 'l':
            event.preventDefault();
            navigate('/deals');
            break;
          case 'a':
            event.preventDefault();
            navigate('/analytics');
            break;
          case 'm':
            event.preventDefault();
            navigate('/mapping');
            break;
          case 'i':
            event.preventDefault();
            navigate('/investments');
            break;
          case 't':
            event.preventDefault();
            navigate('/transactions');
            break;
          case 'r':
            event.preventDefault();
            navigate('/reporting');
            break;
        }
        return;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      if (gKeyTimeout.current) {
        clearTimeout(gKeyTimeout.current);
      }
    };
  }, [
    navigate,
    location.pathname,
    toggleCommandPalette,
    openShortcutsHelp,
    toggleWatchlist,
    toggleCompareMode,
    clearGKey,
  ]);

  return (
    <>
      {children}
      <ShortcutsHelpDialog open={shortcutsHelpOpen} onOpenChange={(open) => !open && closeShortcutsHelp()} />
    </>
  );
}

interface ShortcutsHelpDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function ShortcutsHelpDialog({ open, onOpenChange }: ShortcutsHelpDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Keyboard Shortcuts</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {shortcutGroups.map((group) => (
            <div key={group.title}>
              <h3 className="text-sm font-semibold text-neutral-900 mb-3">
                {group.title}
              </h3>
              <div className="space-y-2">
                {group.shortcuts.map((shortcut, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between py-1.5"
                  >
                    <span className="text-sm text-neutral-600">
                      {shortcut.description}
                    </span>
                    <div className="flex items-center gap-1">
                      {shortcut.keys.map((key, keyIndex) => (
                        <span key={keyIndex} className="flex items-center">
                          <kbd
                            className={cn(
                              'inline-flex h-6 min-w-[24px] items-center justify-center rounded border',
                              'bg-neutral-100 px-1.5 font-mono text-xs font-medium text-neutral-700',
                              'shadow-sm'
                            )}
                          >
                            {key === 'Ctrl' ? modKey : key}
                          </kbd>
                          {keyIndex < shortcut.keys.length - 1 && (
                            <span className="mx-1 text-neutral-400">+</span>
                          )}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 pt-4 border-t text-xs text-neutral-500">
          <p>
            Tip: Press <kbd className="mx-1 px-1.5 py-0.5 rounded bg-neutral-100 font-mono">{modKey}+K</kbd>
            to open the command palette for quick access to all features.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
