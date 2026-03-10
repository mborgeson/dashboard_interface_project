import { useToast } from './useToast';

/**
 * Thin wrapper around useToast providing a consistent notification API.
 *
 * Usage:
 *   const notify = useNotify();
 *   notify.success('Saved!');
 *   notify.error('Something went wrong');
 *   notify.warning('Check your input');
 *   notify.info('Processing...');
 */
export function useNotify() {
  const { success, error, warning, info, dismiss } = useToast();

  return {
    success,
    error,
    warning,
    info,
    dismiss,
  };
}
