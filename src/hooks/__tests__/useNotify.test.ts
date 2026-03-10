import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useNotify } from '../useNotify';
import { useNotificationStore } from '@/stores/notificationStore';

vi.mock('@/stores/notificationStore', () => ({
  useNotificationStore: vi.fn(),
}));

describe('useNotify', () => {
  const mockAddToast = vi.fn().mockReturnValue('toast-id-1');
  const mockRemoveToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useNotificationStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      addToast: mockAddToast,
      removeToast: mockRemoveToast,
    });
  });

  it('returns success, error, warning, info, and dismiss methods', () => {
    const { result } = renderHook(() => useNotify());

    expect(typeof result.current.success).toBe('function');
    expect(typeof result.current.error).toBe('function');
    expect(typeof result.current.warning).toBe('function');
    expect(typeof result.current.info).toBe('function');
    expect(typeof result.current.dismiss).toBe('function');
  });

  it('notify.success delegates to toast system with success type', () => {
    const { result } = renderHook(() => useNotify());

    act(() => {
      result.current.success('Item saved');
    });

    expect(mockAddToast).toHaveBeenCalledWith({
      type: 'success',
      title: 'Item saved',
    });
  });

  it('notify.error delegates to toast system with error type', () => {
    const { result } = renderHook(() => useNotify());

    act(() => {
      result.current.error('Something went wrong');
    });

    expect(mockAddToast).toHaveBeenCalledWith({
      type: 'error',
      title: 'Something went wrong',
    });
  });

  it('notify.warning delegates to toast system with warning type', () => {
    const { result } = renderHook(() => useNotify());

    act(() => {
      result.current.warning('Check your input');
    });

    expect(mockAddToast).toHaveBeenCalledWith({
      type: 'warning',
      title: 'Check your input',
    });
  });

  it('notify.info delegates to toast system with info type', () => {
    const { result } = renderHook(() => useNotify());

    act(() => {
      result.current.info('Processing...');
    });

    expect(mockAddToast).toHaveBeenCalledWith({
      type: 'info',
      title: 'Processing...',
    });
  });

  it('passes additional options through', () => {
    const { result } = renderHook(() => useNotify());

    act(() => {
      result.current.success('Saved', { description: 'Record updated', duration: 3000 });
    });

    expect(mockAddToast).toHaveBeenCalledWith({
      type: 'success',
      title: 'Saved',
      description: 'Record updated',
      duration: 3000,
    });
  });

  it('dismiss calls removeToast', () => {
    const { result } = renderHook(() => useNotify());

    act(() => {
      result.current.dismiss('toast-id-1');
    });

    expect(mockRemoveToast).toHaveBeenCalledWith('toast-id-1');
  });
});
