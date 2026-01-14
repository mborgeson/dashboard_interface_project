import {
  useRef,
  useState,
  useEffect,
  useCallback,
  useMemo,
  type ReactNode,
  type CSSProperties,
} from 'react';
import { cn } from '@/lib/utils';

export interface VirtualListProps<T> {
  /** Array of items to render */
  items: T[];
  /** Render function for each item */
  renderItem: (item: T, index: number) => ReactNode;
  /** Estimated height of each item in pixels (for variable height, provide average) */
  estimateSize: number;
  /** Additional CSS classes for the container */
  className?: string;
  /** Number of items to render outside visible area (overscan) */
  overscan?: number;
  /** Unique key extractor for items */
  getKey?: (item: T, index: number) => string | number;
  /** Height of the container (defaults to 400px if not specified) */
  height?: number | string;
  /** Minimum items before virtualization kicks in */
  virtualizeThreshold?: number;
}

interface ItemMeasurement {
  index: number;
  top: number;
  height: number;
}

/**
 * VirtualList - IntersectionObserver-based virtual scrolling component
 *
 * Efficiently renders large lists by only mounting items that are visible
 * or within the overscan buffer. Uses IntersectionObserver for visibility
 * detection and supports variable height items.
 *
 * @example
 * ```tsx
 * <VirtualList
 *   items={properties}
 *   estimateSize={60}
 *   renderItem={(property, index) => (
 *     <PropertyRow key={property.id} property={property} />
 *   )}
 *   getKey={(property) => property.id}
 * />
 * ```
 */
export function VirtualList<T>({
  items,
  renderItem,
  estimateSize,
  className,
  overscan = 5,
  getKey,
  height = 400,
  virtualizeThreshold = 50,
}: VirtualListProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 20 });
  const [measurements, setMeasurements] = useState<Map<number, number>>(new Map());
  const measurementRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // If items count is below threshold, render all without virtualization
  const shouldVirtualize = items.length >= virtualizeThreshold;

  // Calculate total height and item positions
  const { totalHeight, itemPositions } = useMemo(() => {
    if (!shouldVirtualize) {
      return { totalHeight: 0, itemPositions: [] };
    }

    const positions: ItemMeasurement[] = [];
    let currentTop = 0;

    for (let i = 0; i < items.length; i++) {
      const measuredHeight = measurements.get(i);
      const itemHeight = measuredHeight ?? estimateSize;

      positions.push({
        index: i,
        top: currentTop,
        height: itemHeight,
      });

      currentTop += itemHeight;
    }

    return {
      totalHeight: currentTop,
      itemPositions: positions,
    };
  }, [items.length, measurements, estimateSize, shouldVirtualize]);

  // Binary search to find item at scroll position
  const findItemAtPosition = useCallback(
    (scrollTop: number): number => {
      if (itemPositions.length === 0) return 0;

      let low = 0;
      let high = itemPositions.length - 1;

      while (low <= high) {
        const mid = Math.floor((low + high) / 2);
        const item = itemPositions[mid];

        if (item.top <= scrollTop && item.top + item.height > scrollTop) {
          return mid;
        }

        if (item.top > scrollTop) {
          high = mid - 1;
        } else {
          low = mid + 1;
        }
      }

      return Math.max(0, Math.min(low, itemPositions.length - 1));
    },
    [itemPositions]
  );

  // Handle scroll to update visible range
  const handleScroll = useCallback(() => {
    if (!containerRef.current || !shouldVirtualize) return;

    const { scrollTop, clientHeight } = containerRef.current;

    const startIndex = findItemAtPosition(scrollTop);
    const endIndex = findItemAtPosition(scrollTop + clientHeight);

    // Apply overscan
    const start = Math.max(0, startIndex - overscan);
    const end = Math.min(items.length - 1, endIndex + overscan);

    setVisibleRange((prev) => {
      if (prev.start !== start || prev.end !== end) {
        return { start, end };
      }
      return prev;
    });
  }, [findItemAtPosition, items.length, overscan, shouldVirtualize]);

  // Setup scroll listener
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !shouldVirtualize) return;

    container.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll(); // Initial calculation

    return () => {
      container.removeEventListener('scroll', handleScroll);
    };
  }, [handleScroll, shouldVirtualize]);

  // Measure rendered items
  useEffect(() => {
    if (!shouldVirtualize) return;

    const observer = new ResizeObserver((entries) => {
      const newMeasurements = new Map(measurements);
      let hasChanges = false;

      for (const entry of entries) {
        const target = entry.target as HTMLElement;
        const index = parseInt(target.dataset.virtualIndex ?? '-1', 10);

        if (index >= 0) {
          const height = entry.contentRect.height;
          const currentHeight = newMeasurements.get(index);

          if (currentHeight !== height) {
            newMeasurements.set(index, height);
            hasChanges = true;
          }
        }
      }

      if (hasChanges) {
        setMeasurements(newMeasurements);
      }
    });

    // Observe all mounted items
    measurementRefs.current.forEach((element) => {
      observer.observe(element);
    });

    return () => {
      observer.disconnect();
    };
  }, [visibleRange, shouldVirtualize, measurements]);

  // Register measurement ref
  const registerRef = useCallback((index: number, element: HTMLDivElement | null) => {
    if (element) {
      measurementRefs.current.set(index, element);
    } else {
      measurementRefs.current.delete(index);
    }
  }, []);

  // Non-virtualized render for small lists
  if (!shouldVirtualize) {
    return (
      <div className={cn('overflow-auto', className)} style={{ height }}>
        {items.map((item, index) => (
          <div key={getKey ? getKey(item, index) : index}>
            {renderItem(item, index)}
          </div>
        ))}
      </div>
    );
  }

  // Get visible items
  const visibleItems: Array<{ item: T; index: number; position: ItemMeasurement }> = [];
  for (let i = visibleRange.start; i <= visibleRange.end && i < items.length; i++) {
    visibleItems.push({
      item: items[i],
      index: i,
      position: itemPositions[i],
    });
  }

  return (
    <div
      ref={containerRef}
      className={cn('overflow-auto relative', className)}
      style={{ height }}
    >
      {/* Spacer to maintain scroll height */}
      <div style={{ height: totalHeight, position: 'relative' }}>
        {visibleItems.map(({ item, index, position }) => {
          const style: CSSProperties = {
            position: 'absolute',
            top: position.top,
            left: 0,
            right: 0,
            minHeight: estimateSize,
          };

          return (
            <div
              key={getKey ? getKey(item, index) : index}
              ref={(el) => registerRef(index, el)}
              data-virtual-index={index}
              style={style}
            >
              {renderItem(item, index)}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Hook for simple virtualization needs
 * Returns visible items and container props
 */
export function useVirtualization<T>(
  items: T[],
  options: {
    estimateSize: number;
    containerHeight: number;
    overscan?: number;
  }
) {
  const { estimateSize, containerHeight, overscan = 5 } = options;
  const [scrollTop, setScrollTop] = useState(0);

  const visibleCount = Math.ceil(containerHeight / estimateSize);
  const startIndex = Math.max(0, Math.floor(scrollTop / estimateSize) - overscan);
  const endIndex = Math.min(
    items.length,
    startIndex + visibleCount + overscan * 2
  );

  const visibleItems = items.slice(startIndex, endIndex);
  const totalHeight = items.length * estimateSize;
  const offsetTop = startIndex * estimateSize;

  const onScroll = useCallback((event: React.UIEvent<HTMLElement>) => {
    setScrollTop(event.currentTarget.scrollTop);
  }, []);

  return {
    visibleItems,
    startIndex,
    totalHeight,
    offsetTop,
    onScroll,
    containerProps: {
      onScroll,
      style: { height: containerHeight, overflow: 'auto' as const },
    },
    innerProps: {
      style: { height: totalHeight, position: 'relative' as const },
    },
    itemProps: (index: number) => ({
      style: {
        position: 'absolute' as const,
        top: (startIndex + index) * estimateSize,
        left: 0,
        right: 0,
        height: estimateSize,
      },
    }),
  };
}

export default VirtualList;
