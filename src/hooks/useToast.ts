import { useCallback } from 'react';
import { useNotificationStore } from '@/stores/notificationStore';
import type { ToastOptions, ToastType } from '@/types/notification';

export function useToast() {
  const { addToast, removeToast } = useNotificationStore();

  const toast = useCallback(
    (options: ToastOptions) => {
      return addToast(options);
    },
    [addToast]
  );

  const createToastHelper = useCallback(
    (type: ToastType) => {
      return (
        title: string,
        options?: Omit<ToastOptions, 'type' | 'title'>
      ) => {
        return addToast({
          type,
          title,
          ...options,
        });
      };
    },
    [addToast]
  );

  const success = useCallback(
    (title: string, options?: Omit<ToastOptions, 'type' | 'title'>) => {
      return createToastHelper('success')(title, options);
    },
    [createToastHelper]
  );

  const error = useCallback(
    (title: string, options?: Omit<ToastOptions, 'type' | 'title'>) => {
      return createToastHelper('error')(title, options);
    },
    [createToastHelper]
  );

  const warning = useCallback(
    (title: string, options?: Omit<ToastOptions, 'type' | 'title'>) => {
      return createToastHelper('warning')(title, options);
    },
    [createToastHelper]
  );

  const info = useCallback(
    (title: string, options?: Omit<ToastOptions, 'type' | 'title'>) => {
      return createToastHelper('info')(title, options);
    },
    [createToastHelper]
  );

  const dismiss = useCallback(
    (id: string) => {
      removeToast(id);
    },
    [removeToast]
  );

  return {
    toast,
    success,
    error,
    warning,
    info,
    dismiss,
  };
}
