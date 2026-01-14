import { useState, useCallback, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus,
  X,
  Search,
  RefreshCw,
  FileBarChart,
  Command,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useQuickActions } from '@/contexts/QuickActionsContext';
import { useToast } from '@/hooks/useToast';

interface FABAction {
  id: string;
  label: string;
  icon: React.ReactNode;
  action: () => void;
  color: string;
}

export function FloatingActionButton() {
  const [isExpanded, setIsExpanded] = useState(false);
  const navigate = useNavigate();
  const { openCommandPalette } = useQuickActions();
  const { info } = useToast();
  const fabRef = useRef<HTMLDivElement>(null);

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (fabRef.current && !fabRef.current.contains(event.target as Node)) {
        setIsExpanded(false);
      }
    };

    if (isExpanded) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isExpanded]);

  // Close on escape
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsExpanded(false);
      }
    };

    if (isExpanded) {
      document.addEventListener('keydown', handleEscape);
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isExpanded]);

  const toggleExpanded = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  const handleAction = useCallback(
    (action: () => void) => {
      action();
      setIsExpanded(false);
    },
    []
  );

  const actions: FABAction[] = [
    {
      id: 'add-deal',
      label: 'Add Deal',
      icon: <FileBarChart className="w-5 h-5" />,
      action: () => {
        navigate('/deals');
        info('Navigate to deals to add a new deal');
      },
      color: 'bg-blue-500 hover:bg-blue-600',
    },
    {
      id: 'quick-search',
      label: 'Quick Search',
      icon: <Search className="w-5 h-5" />,
      action: () => openCommandPalette(),
      color: 'bg-purple-500 hover:bg-purple-600',
    },
    {
      id: 'command-palette',
      label: 'Commands',
      icon: <Command className="w-5 h-5" />,
      action: () => openCommandPalette(),
      color: 'bg-green-500 hover:bg-green-600',
    },
    {
      id: 'refresh-data',
      label: 'Refresh Data',
      icon: <RefreshCw className="w-5 h-5" />,
      action: () => {
        // Trigger data refresh - would integrate with react-query
        window.location.reload();
        info('Refreshing data...');
      },
      color: 'bg-orange-500 hover:bg-orange-600',
    },
  ];

  return (
    <div
      ref={fabRef}
      className={cn(
        'fixed bottom-6 right-6 z-50',
        'lg:hidden' // Only show on mobile/tablet
      )}
    >
      {/* Action buttons */}
      <div
        className={cn(
          'flex flex-col-reverse items-center gap-3 mb-3',
          'transition-all duration-300 ease-out',
          isExpanded ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
      >
        {actions.map((action, index) => (
          <div
            key={action.id}
            className={cn(
              'flex items-center gap-3 transition-all duration-300',
              isExpanded
                ? 'translate-y-0 opacity-100'
                : 'translate-y-4 opacity-0'
            )}
            style={{
              transitionDelay: isExpanded ? `${index * 50}ms` : '0ms',
            }}
          >
            {/* Label */}
            <span
              className={cn(
                'px-3 py-1.5 rounded-lg text-sm font-medium',
                'bg-neutral-900 text-white shadow-lg',
                'whitespace-nowrap'
              )}
            >
              {action.label}
            </span>
            {/* Action button */}
            <button
              onClick={() => handleAction(action.action)}
              className={cn(
                'w-12 h-12 rounded-full shadow-lg',
                'flex items-center justify-center text-white',
                'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500',
                'transition-transform hover:scale-110 active:scale-95',
                action.color
              )}
              aria-label={action.label}
            >
              {action.icon}
            </button>
          </div>
        ))}
      </div>

      {/* Main FAB button */}
      <button
        onClick={toggleExpanded}
        className={cn(
          'w-14 h-14 rounded-full shadow-xl',
          'flex items-center justify-center text-white',
          'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500',
          'transition-all duration-300',
          isExpanded
            ? 'bg-neutral-700 hover:bg-neutral-800 rotate-45'
            : 'bg-primary-500 hover:bg-primary-600 rotate-0'
        )}
        aria-label={isExpanded ? 'Close quick actions' : 'Open quick actions'}
        aria-expanded={isExpanded}
      >
        {isExpanded ? (
          <X className="w-6 h-6" />
        ) : (
          <Plus className="w-6 h-6" />
        )}
      </button>

      {/* Backdrop */}
      {isExpanded && (
        <div
          className="fixed inset-0 bg-black/20 -z-10"
          aria-hidden="true"
        />
      )}
    </div>
  );
}
