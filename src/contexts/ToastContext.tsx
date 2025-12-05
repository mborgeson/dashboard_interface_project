import type { ReactNode } from 'react';
import { ToastContainer } from '@/components/ui/toast-container';

interface ToastProviderProps {
  children: ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps) {
  return (
    <>
      {children}
      <ToastContainer />
    </>
  );
}
