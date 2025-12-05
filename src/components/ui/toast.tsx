import { useEffect, useState } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';
import type { Toast as ToastType } from '@/types/notification';
import { cn } from '@/lib/utils';

interface ToastProps {
  toast: ToastType;
  onRemove: (id: string) => void;
}

const iconMap = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const colorMap = {
  success: {
    bg: 'bg-green-50 dark:bg-green-950',
    border: 'border-green-500',
    icon: 'text-green-500',
    text: 'text-green-900 dark:text-green-100',
    progress: 'bg-green-500',
  },
  error: {
    bg: 'bg-red-50 dark:bg-red-950',
    border: 'border-red-500',
    icon: 'text-red-500',
    text: 'text-red-900 dark:text-red-100',
    progress: 'bg-red-500',
  },
  warning: {
    bg: 'bg-amber-50 dark:bg-amber-950',
    border: 'border-amber-500',
    icon: 'text-amber-500',
    text: 'text-amber-900 dark:text-amber-100',
    progress: 'bg-amber-500',
  },
  info: {
    bg: 'bg-blue-50 dark:bg-blue-950',
    border: 'border-blue-500',
    icon: 'text-blue-500',
    text: 'text-blue-900 dark:text-blue-100',
    progress: 'bg-blue-500',
  },
};

export function Toast({ toast, onRemove }: ToastProps) {
  const [isExiting, setIsExiting] = useState(false);
  const [progress, setProgress] = useState(100);
  
  const Icon = iconMap[toast.type];
  const colors = colorMap[toast.type];
  const duration = toast.duration ?? 5000;

  useEffect(() => {
    if (duration <= 0) return;

    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const remaining = Math.max(0, 100 - (elapsed / duration) * 100);
      setProgress(remaining);

      if (remaining === 0) {
        clearInterval(interval);
      }
    }, 16); // ~60fps

    return () => clearInterval(interval);
  }, [duration]);

  const handleClose = () => {
    setIsExiting(true);
    setTimeout(() => {
      onRemove(toast.id);
    }, 300);
  };

  return (
    <div
      className={cn(
        'relative w-96 rounded-lg border-l-4 shadow-lg transition-all duration-300 overflow-hidden',
        colors.bg,
        colors.border,
        isExiting
          ? 'translate-x-full opacity-0'
          : 'translate-x-0 opacity-100 animate-in slide-in-from-right'
      )}
    >
      <div className="p-4">
        <div className="flex items-start gap-3">
          <Icon className={cn('h-5 w-5 flex-shrink-0 mt-0.5', colors.icon)} />
          
          <div className="flex-1 min-w-0">
            <p className={cn('font-semibold text-sm', colors.text)}>
              {toast.title}
            </p>
            
            {toast.description && (
              <p className={cn('mt-1 text-sm opacity-90', colors.text)}>
                {toast.description}
              </p>
            )}
            
            {toast.action && (
              <button
                onClick={toast.action.onClick}
                className={cn(
                  'mt-2 text-sm font-medium underline-offset-4 hover:underline',
                  colors.icon
                )}
              >
                {toast.action.label}
              </button>
            )}
          </div>
          
          <button
            onClick={handleClose}
            className={cn(
              'flex-shrink-0 rounded-md p-1 transition-colors hover:bg-black/10 dark:hover:bg-white/10',
              colors.text
            )}
            aria-label="Close notification"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
      
      {duration > 0 && (
        <div className="h-1 bg-black/10 dark:bg-white/10">
          <div
            className={cn('h-full transition-all duration-100 ease-linear', colors.progress)}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
}
