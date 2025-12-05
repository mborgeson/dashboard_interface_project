export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
  duration?: number; // ms, default 5000
  action?: {
    label: string;
    onClick: () => void;
  };
}

export interface ToastOptions extends Omit<Toast, 'id'> {
  id?: string;
}

export interface AlertBannerProps {
  variant: ToastType;
  title: string;
  description?: string;
  dismissible?: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
  onDismiss?: () => void;
}
