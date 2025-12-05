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
      setTimeout(() => {
        get().removeToast(id);
      }, duration);
    }
    
    return id;
  },
  
  removeToast: (id: string) => {
    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id),
    }));
  },
  
  clearAll: () => {
    set({ toasts: [] });
  },
}));
