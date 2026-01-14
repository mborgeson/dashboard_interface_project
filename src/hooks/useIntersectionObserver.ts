import { useState, useEffect, useRef, useCallback, type RefObject } from 'react';

export interface UseIntersectionObserverOptions {
  /**
   * Element that is used as the viewport for checking visibility.
   * Defaults to the browser viewport if not specified.
   */
  root?: Element | null;
  /**
   * Margin around the root element. Can be specified similarly to CSS margin.
   * Default: '0px'
   */
  rootMargin?: string;
  /**
   * A threshold indicating the percentage of the target element's visibility
   * the observer callback should execute. Can be a single number or array.
   * Default: 0 (triggers as soon as even one pixel is visible)
   */
  threshold?: number | number[];
  /**
   * If true, the observer will disconnect after the first intersection.
   * Useful for lazy loading where you only need to detect once.
   * Default: false
   */
  triggerOnce?: boolean;
  /**
   * Whether the observer should be active.
   * Default: true
   */
  enabled?: boolean;
}

export interface UseIntersectionObserverReturn<T extends Element> {
  /**
   * Ref to attach to the target element
   */
  ref: RefObject<T | null>;
  /**
   * Whether the element is currently intersecting the viewport
   */
  isIntersecting: boolean;
  /**
   * The full IntersectionObserverEntry for advanced use cases
   */
  entry: IntersectionObserverEntry | null;
  /**
   * Function to manually reset the observer (useful with triggerOnce)
   */
  reset: () => void;
}

/**
 * Custom hook for observing element intersection with viewport using IntersectionObserver API.
 * Useful for lazy loading images, infinite scroll, or triggering animations on scroll.
 *
 * @example
 * ```tsx
 * const { ref, isIntersecting } = useIntersectionObserver<HTMLDivElement>({
 *   threshold: 0.1,
 *   triggerOnce: true
 * });
 *
 * return <div ref={ref}>{isIntersecting ? 'Visible!' : 'Not visible'}</div>;
 * ```
 */
export function useIntersectionObserver<T extends Element = Element>(
  options: UseIntersectionObserverOptions = {}
): UseIntersectionObserverReturn<T> {
  const {
    root = null,
    rootMargin = '0px',
    threshold = 0,
    triggerOnce = false,
    enabled = true,
  } = options;

  const ref = useRef<T>(null);
  const [entry, setEntry] = useState<IntersectionObserverEntry | null>(null);
  const [isIntersecting, setIsIntersecting] = useState(false);
  const [hasTriggered, setHasTriggered] = useState(false);

  const reset = useCallback(() => {
    setEntry(null);
    setIsIntersecting(false);
    setHasTriggered(false);
  }, []);

  useEffect(() => {
    const element = ref.current;

    // Skip if disabled, no element, or already triggered (when triggerOnce is true)
    if (!enabled || !element || (triggerOnce && hasTriggered)) {
      return;
    }

    // Check for IntersectionObserver support
    if (typeof IntersectionObserver === 'undefined') {
      // Fallback: assume element is visible if IntersectionObserver is not supported
      setIsIntersecting(true);
      setHasTriggered(true);
      return;
    }

    const observerCallback: IntersectionObserverCallback = ([observerEntry]) => {
      setEntry(observerEntry);
      setIsIntersecting(observerEntry.isIntersecting);

      if (observerEntry.isIntersecting && triggerOnce) {
        setHasTriggered(true);
      }
    };

    const observer = new IntersectionObserver(observerCallback, {
      root,
      rootMargin,
      threshold,
    });

    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, [enabled, root, rootMargin, threshold, triggerOnce, hasTriggered]);

  return {
    ref,
    isIntersecting,
    entry,
    reset,
  };
}

export default useIntersectionObserver;
