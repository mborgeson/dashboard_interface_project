import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { useNotificationStore } from './notificationStore';

describe('notificationStore', () => {
  beforeEach(() => {
    // Reset store before each test
    useNotificationStore.setState({ toasts: [] });
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('addToast', () => {
    it('adds a toast notification', () => {
      useNotificationStore.getState().addToast({
        title: 'Test Toast',
        description: 'Test description',
        type: 'success',
      });

      const toasts = useNotificationStore.getState().toasts;
      expect(toasts).toHaveLength(1);
      expect(toasts[0].title).toBe('Test Toast');
      expect(toasts[0].type).toBe('success');
    });

    it('generates unique IDs for each toast', () => {
      useNotificationStore.getState().addToast({ title: 'Toast 1', type: 'info' });
      useNotificationStore.getState().addToast({ title: 'Toast 2', type: 'info' });

      const toasts = useNotificationStore.getState().toasts;
      expect(toasts[0].id).not.toBe(toasts[1].id);
    });

    it('auto-dismisses toast after duration', () => {
      useNotificationStore.getState().addToast({
        title: 'Auto dismiss',
        type: 'info',
        duration: 3000,
      });

      expect(useNotificationStore.getState().toasts).toHaveLength(1);

      // Fast-forward past the duration
      vi.advanceTimersByTime(3100);

      expect(useNotificationStore.getState().toasts).toHaveLength(0);
    });

    it('returns the toast id', () => {
      const id = useNotificationStore.getState().addToast({
        title: 'Test',
        type: 'info',
      });

      expect(typeof id).toBe('string');
      expect(id).toContain('toast-');
    });
  });

  describe('removeToast', () => {
    it('removes a specific toast by ID', () => {
      const id1 = useNotificationStore.getState().addToast({ title: 'Toast 1', type: 'info', duration: 0 });
      useNotificationStore.getState().addToast({ title: 'Toast 2', type: 'info', duration: 0 });

      useNotificationStore.getState().removeToast(id1);

      const updatedToasts = useNotificationStore.getState().toasts;
      expect(updatedToasts).toHaveLength(1);
      expect(updatedToasts[0].title).toBe('Toast 2');
    });
  });

  describe('clearAll', () => {
    it('removes all toasts', () => {
      useNotificationStore.getState().addToast({ title: 'Toast 1', type: 'info', duration: 0 });
      useNotificationStore.getState().addToast({ title: 'Toast 2', type: 'info', duration: 0 });

      useNotificationStore.getState().clearAll();

      expect(useNotificationStore.getState().toasts).toHaveLength(0);
    });
  });

  describe('toast types', () => {
    it('creates toast with success type', () => {
      useNotificationStore.getState().addToast({
        title: 'Success',
        type: 'success',
      });
      expect(useNotificationStore.getState().toasts[0].type).toBe('success');
    });

    it('creates toast with error type', () => {
      useNotificationStore.getState().addToast({
        title: 'Error',
        type: 'error',
      });
      expect(useNotificationStore.getState().toasts[0].type).toBe('error');
    });

    it('creates toast with warning type', () => {
      useNotificationStore.getState().addToast({
        title: 'Warning',
        type: 'warning',
      });
      expect(useNotificationStore.getState().toasts[0].type).toBe('warning');
    });

    it('creates toast with info type', () => {
      useNotificationStore.getState().addToast({
        title: 'Info',
        type: 'info',
      });
      expect(useNotificationStore.getState().toasts[0].type).toBe('info');
    });
  });

  describe('default duration', () => {
    it('uses default duration of 5000ms when not specified', () => {
      useNotificationStore.getState().addToast({
        title: 'Default duration',
        type: 'info',
      });

      expect(useNotificationStore.getState().toasts).toHaveLength(1);

      // Should still exist at 4900ms
      vi.advanceTimersByTime(4900);
      expect(useNotificationStore.getState().toasts).toHaveLength(1);

      // Should be removed after 5000ms
      vi.advanceTimersByTime(200);
      expect(useNotificationStore.getState().toasts).toHaveLength(0);
    });
  });
});
