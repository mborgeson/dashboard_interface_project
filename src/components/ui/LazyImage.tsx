import * as React from 'react';
import { useState, useCallback, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { useIntersectionObserver } from '@/hooks/useIntersectionObserver';
import { Skeleton } from './skeleton';

export interface LazyImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  /**
   * The source URL of the full-resolution image
   */
  src: string;
  /**
   * Alternative text for the image (required for accessibility)
   */
  alt: string;
  /**
   * Optional low-resolution placeholder image URL for blur-up effect
   */
  placeholder?: string;
  /**
   * Aspect ratio of the image container (e.g., "16/9", "4/3", "1/1")
   * Used to prevent layout shift while loading
   */
  aspectRatio?: string;
  /**
   * srcSet for responsive images
   */
  srcSet?: string;
  /**
   * sizes attribute for responsive images
   */
  sizes?: string;
  /**
   * Custom className for the container
   */
  containerClassName?: string;
  /**
   * Custom className for the image element
   */
  className?: string;
  /**
   * Margin around the viewport for triggering load (IntersectionObserver rootMargin)
   * Default: '100px' (preload when within 100px of viewport)
   */
  rootMargin?: string;
  /**
   * Callback fired when the image has successfully loaded
   */
  onLoad?: () => void;
  /**
   * Callback fired when the image fails to load
   */
  onError?: () => void;
  /**
   * Custom error fallback element
   */
  errorFallback?: React.ReactNode;
  /**
   * Whether to show the loading skeleton
   * Default: true
   */
  showSkeleton?: boolean;
  /**
   * Duration of the blur-up transition in milliseconds
   * Default: 300
   */
  transitionDuration?: number;
}

type ImageState = 'idle' | 'loading' | 'loaded' | 'error';

/**
 * LazyImage component with IntersectionObserver-based lazy loading,
 * blur-up placeholder effect, loading skeleton, and error fallback.
 *
 * @example
 * ```tsx
 * <LazyImage
 *   src="/images/hero.jpg"
 *   alt="Hero image"
 *   placeholder="/images/hero-placeholder.jpg"
 *   aspectRatio="16/9"
 *   srcSet="/images/hero-400.jpg 400w, /images/hero-800.jpg 800w"
 *   sizes="(max-width: 600px) 400px, 800px"
 * />
 * ```
 */
export const LazyImage = React.forwardRef<HTMLDivElement, LazyImageProps>(
  (
    {
      src,
      alt,
      placeholder,
      aspectRatio,
      srcSet,
      sizes,
      containerClassName,
      className,
      rootMargin = '100px',
      onLoad,
      onError,
      errorFallback,
      showSkeleton = true,
      transitionDuration = 300,
      ...imgProps
    },
    forwardedRef
  ) => {
    const [imageState, setImageState] = useState<ImageState>('idle');
    const [showPlaceholder, setShowPlaceholder] = useState(!!placeholder);
    const imageRef = useRef<HTMLImageElement>(null);

    // Use intersection observer to detect when image enters viewport
    const { ref: observerRef, isIntersecting } = useIntersectionObserver<HTMLDivElement>({
      rootMargin,
      triggerOnce: true,
      threshold: 0.01,
    });

    // Merge refs for the container
    const mergedRef = useCallback(
      (node: HTMLDivElement | null) => {
        // Set the observer ref
        // eslint-disable-next-line react-hooks/immutability
        (observerRef as React.MutableRefObject<HTMLDivElement | null>).current = node;

        // Set the forwarded ref
        if (typeof forwardedRef === 'function') {
          forwardedRef(node);
        } else if (forwardedRef) {
          forwardedRef.current = node;
        }
      },
      [forwardedRef, observerRef]
    );

    // Start loading when the image becomes visible
    useEffect(() => {
      if (isIntersecting && imageState === 'idle') {
        setImageState('loading');
      }
    }, [isIntersecting, imageState]);

    const handleImageLoad = useCallback(() => {
      setImageState('loaded');

      // Start fade-out of placeholder after a brief delay
      const timer = setTimeout(() => {
        setShowPlaceholder(false);
      }, transitionDuration);

      onLoad?.();

      return () => clearTimeout(timer);
    }, [onLoad, transitionDuration]);

    const handleImageError = useCallback(() => {
      setImageState('error');
      setShowPlaceholder(false);
      onError?.();
    }, [onError]);

    // Compute aspect ratio style
    const aspectRatioStyle: React.CSSProperties = aspectRatio
      ? { aspectRatio }
      : {};

    const isLoading = imageState === 'idle' || imageState === 'loading';
    const isLoaded = imageState === 'loaded';
    const hasError = imageState === 'error';

    return (
      <div
        ref={mergedRef}
        className={cn(
          'relative overflow-hidden bg-muted',
          containerClassName
        )}
        style={aspectRatioStyle}
        data-testid="lazy-image-container"
      >
        {/* Loading skeleton */}
        {showSkeleton && isLoading && (
          <Skeleton
            className="absolute inset-0 z-10"
            data-testid="lazy-image-skeleton"
          />
        )}

        {/* Low-resolution placeholder for blur-up effect */}
        {placeholder && showPlaceholder && (
          <img
            src={placeholder}
            alt=""
            aria-hidden="true"
            className={cn(
              'absolute inset-0 h-full w-full object-cover blur-lg scale-105',
              'transition-opacity',
              isLoaded ? 'opacity-0' : 'opacity-100',
              className
            )}
            style={{ transitionDuration: `${transitionDuration}ms` }}
            data-testid="lazy-image-placeholder"
          />
        )}

        {/* Main image */}
        {(isIntersecting || imageState !== 'idle') && !hasError && (
          <img
            ref={imageRef}
            src={src}
            alt={alt}
            srcSet={srcSet}
            sizes={sizes}
            onLoad={handleImageLoad}
            onError={handleImageError}
            className={cn(
              'h-full w-full object-cover',
              'transition-opacity',
              isLoaded ? 'opacity-100' : 'opacity-0',
              className
            )}
            style={{ transitionDuration: `${transitionDuration}ms` }}
            data-testid="lazy-image"
            {...imgProps}
          />
        )}

        {/* Error fallback */}
        {hasError && (
          <div
            className="absolute inset-0 flex items-center justify-center bg-muted"
            data-testid="lazy-image-error"
          >
            {errorFallback || (
              <div className="flex flex-col items-center gap-2 text-muted-foreground">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="h-8 w-8"
                  aria-hidden="true"
                >
                  <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
                  <circle cx="9" cy="9" r="2" />
                  <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
                </svg>
                <span className="text-sm">Failed to load image</span>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }
);

LazyImage.displayName = 'LazyImage';

export default LazyImage;
