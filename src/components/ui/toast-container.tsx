import { createPortal } from 'react-dom';
import { useNotificationStore } from '@/stores/notificationStore';
import { Toast } from './toast';

export function ToastContainer() {
  const { toasts, removeToast } = useNotificationStore();
  
  // Show maximum 5 toasts
  const visibleToasts = toasts.slice(-5);

  if (visibleToasts.length === 0) {
    return null;
  }

  return createPortal(
    <div
      className="fixed bottom-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none"
      aria-live="polite"
      aria-atomic="false"
    >
      {visibleToasts.map((toast) => (
        <div key={toast.id} className="pointer-events-auto">
          <Toast toast={toast} onRemove={removeToast} />
        </div>
      ))}
    </div>,
    document.body
  );
}
