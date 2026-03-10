import { create } from 'zustand';
import type { Toast, ToastOptions } from '@/types/notification';

interface NotificationState {
  toasts: Toast[];
  addToast: (toast: ToastOptions) => string;
  removeToast: (id: string) => void;
  clearAll: () => void;
}

const generateId = (): string => {
  return `toast-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
};

/** Map of toast ID -> auto-removal timer ID */
const timerMap = new Map<string, ReturnType<typeof setTimeout>>();

export const useNotificationStore = create<NotificationState>((set, get) => ({
  toasts: [],

  addToast: (toast: ToastOptions) => {
    const id = toast.id || generateId();
    const duration = toast.duration ?? 5000;

    const newToast: Toast = {
      ...toast,
      id,
      duration,
    };

    set((state) => ({
      toasts: [...state.toasts, newToast],
    }));

    // Auto-remove after duration
    if (duration > 0) {
      const timerId = setTimeout(() => {
        timerMap.delete(id);
        get().removeToast(id);
      }, duration);
      timerMap.set(id, timerId);
    }

    return id;
  },

  removeToast: (id: string) => {
    // Clear the auto-removal timer if it exists
    const timerId = timerMap.get(id);
    if (timerId !== undefined) {
      clearTimeout(timerId);
      timerMap.delete(id);
    }

    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id),
    }));
  },

  clearAll: () => {
    // Clear all pending auto-removal timers
    for (const timerId of timerMap.values()) {
      clearTimeout(timerId);
    }
    timerMap.clear();

    set({ toasts: [] });
  },
}));
