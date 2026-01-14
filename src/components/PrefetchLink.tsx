/**
 * PrefetchLink Component
 *
 * A wrapper around React Router's NavLink that triggers prefetching
 * on hover/focus for improved navigation performance.
 *
 * Features:
 * - Prefetch on hover (with debounce)
 * - Prefetch on focus (for keyboard navigation)
 * - Optional eager prefetch on viewport entry
 * - Supports all NavLink props
 */

import { forwardRef, useEffect, useRef, useCallback } from 'react';
import { NavLink, type NavLinkProps } from 'react-router-dom';
import { usePrefetch, type UsePrefetchOptions } from '@/hooks/usePrefetch';

export interface PrefetchLinkProps extends NavLinkProps {
  /**
   * Prefetch options passed to usePrefetch hook
   */
  prefetchOptions?: UsePrefetchOptions;
  /**
   * Enable eager prefetching when link enters viewport
   * Uses IntersectionObserver for efficient detection
   * @default false
   */
  eagerPrefetch?: boolean;
  /**
   * Threshold for IntersectionObserver (0-1)
   * Only used when eagerPrefetch is true
   * @default 0.5
   */
  intersectionThreshold?: number;
  /**
   * Root margin for IntersectionObserver
   * Allows prefetching before element is fully visible
   * @default '50px'
   */
  intersectionRootMargin?: string;
  /**
   * Disable prefetching entirely
   * Useful for external links or when prefetching should be conditional
   * @default false
   */
  disablePrefetch?: boolean;
}

/**
 * NavLink wrapper that prefetches route data and components on hover/focus
 *
 * @example
 * ```tsx
 * // Basic usage
 * <PrefetchLink to="/investments">Investments</PrefetchLink>
 *
 * // With eager prefetch on viewport entry
 * <PrefetchLink to="/deals" eagerPrefetch>Deals</PrefetchLink>
 *
 * // With custom prefetch options
 * <PrefetchLink
 *   to="/market"
 *   prefetchOptions={{ prefetchComponent: false }}
 * >
 *   Market Data
 * </PrefetchLink>
 *
 * // Disabled prefetch
 * <PrefetchLink to="/external" disablePrefetch>
 *   External Link
 * </PrefetchLink>
 * ```
 */
export const PrefetchLink = forwardRef<HTMLAnchorElement, PrefetchLinkProps>(
  (
    {
      to,
      prefetchOptions,
      eagerPrefetch = false,
      intersectionThreshold = 0.5,
      intersectionRootMargin = '50px',
      disablePrefetch = false,
      onMouseEnter,
      onMouseLeave,
      onFocus,
      onBlur,
      children,
      ...props
    },
    ref
  ) => {
    const { prefetch, cancelPrefetch, isPrefetched } = usePrefetch(prefetchOptions);
    const linkRef = useRef<HTMLAnchorElement | null>(null);
    const observerRef = useRef<IntersectionObserver | null>(null);

    // Resolve the route path from the `to` prop
    const routePath = typeof to === 'string' ? to : to.pathname || '';

    // Handle mouse enter - trigger prefetch
    const handleMouseEnter = useCallback(
      (event: React.MouseEvent<HTMLAnchorElement>) => {
        if (!disablePrefetch && routePath) {
          prefetch(routePath);
        }
        onMouseEnter?.(event);
      },
      [disablePrefetch, routePath, prefetch, onMouseEnter]
    );

    // Handle mouse leave - cancel pending prefetch
    const handleMouseLeave = useCallback(
      (event: React.MouseEvent<HTMLAnchorElement>) => {
        if (!disablePrefetch) {
          cancelPrefetch();
        }
        onMouseLeave?.(event);
      },
      [disablePrefetch, cancelPrefetch, onMouseLeave]
    );

    // Handle focus - trigger prefetch (for keyboard navigation)
    const handleFocus = useCallback(
      (event: React.FocusEvent<HTMLAnchorElement>) => {
        if (!disablePrefetch && routePath) {
          prefetch(routePath);
        }
        onFocus?.(event);
      },
      [disablePrefetch, routePath, prefetch, onFocus]
    );

    // Handle blur - cancel pending prefetch
    const handleBlur = useCallback(
      (event: React.FocusEvent<HTMLAnchorElement>) => {
        if (!disablePrefetch) {
          cancelPrefetch();
        }
        onBlur?.(event);
      },
      [disablePrefetch, cancelPrefetch, onBlur]
    );

    // Set up ref callback to handle both internal and forwarded refs
    const setRefs = useCallback(
      (element: HTMLAnchorElement | null) => {
        linkRef.current = element;

        // Handle forwarded ref
        if (typeof ref === 'function') {
          ref(element);
        } else if (ref) {
          ref.current = element;
        }
      },
      [ref]
    );

    // Set up IntersectionObserver for eager prefetching
    useEffect(() => {
      if (!eagerPrefetch || disablePrefetch || !routePath) {
        return;
      }

      // Skip if already prefetched
      if (isPrefetched(routePath)) {
        return;
      }

      // Skip if IntersectionObserver is not supported
      if (typeof IntersectionObserver === 'undefined') {
        return;
      }

      const element = linkRef.current;
      if (!element) {
        return;
      }

      // Create observer
      observerRef.current = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              prefetch(routePath);
              // Disconnect after prefetching
              observerRef.current?.disconnect();
            }
          });
        },
        {
          threshold: intersectionThreshold,
          rootMargin: intersectionRootMargin,
        }
      );

      // Start observing
      observerRef.current.observe(element);

      // Cleanup
      return () => {
        observerRef.current?.disconnect();
      };
    }, [
      eagerPrefetch,
      disablePrefetch,
      routePath,
      intersectionThreshold,
      intersectionRootMargin,
      prefetch,
      isPrefetched,
    ]);

    return (
      <NavLink
        ref={setRefs}
        to={to}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onFocus={handleFocus}
        onBlur={handleBlur}
        {...props}
      >
        {children}
      </NavLink>
    );
  }
);

PrefetchLink.displayName = 'PrefetchLink';

export default PrefetchLink;
