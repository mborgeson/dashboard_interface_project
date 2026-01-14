import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@/test/test-utils';
import { LazyImage } from './LazyImage';

// Mock IntersectionObserver as a class
let intersectionCallback: IntersectionObserverCallback | null = null;
const mockObserve = vi.fn();
const mockDisconnect = vi.fn();
const mockUnobserve = vi.fn();

class MockIntersectionObserver implements IntersectionObserver {
  readonly root: Element | Document | null = null;
  readonly rootMargin: string = '';
  readonly thresholds: ReadonlyArray<number> = [];

  constructor(callback: IntersectionObserverCallback) {
    intersectionCallback = callback;
  }

  observe = mockObserve;
  disconnect = mockDisconnect;
  unobserve = mockUnobserve;
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
}

beforeEach(() => {
  vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
  intersectionCallback = null;
});

// Helper to simulate intersection
const simulateIntersection = (isIntersecting: boolean) => {
  if (intersectionCallback) {
    act(() => {
      intersectionCallback!(
        [
          {
            isIntersecting,
            boundingClientRect: {} as DOMRectReadOnly,
            intersectionRatio: isIntersecting ? 1 : 0,
            intersectionRect: {} as DOMRectReadOnly,
            rootBounds: null,
            target: document.createElement('div'),
            time: Date.now(),
          },
        ],
        new MockIntersectionObserver(() => {})
      );
    });
  }
};

describe('LazyImage', () => {
  it('renders with container', () => {
    render(<LazyImage src="/test.jpg" alt="Test image" />);
    expect(screen.getByTestId('lazy-image-container')).toBeInTheDocument();
  });

  it('shows skeleton while loading', () => {
    render(<LazyImage src="/test.jpg" alt="Test image" />);
    expect(screen.getByTestId('lazy-image-skeleton')).toBeInTheDocument();
  });

  it('does not render image until intersection occurs', () => {
    render(<LazyImage src="/test.jpg" alt="Test image" />);
    expect(screen.queryByTestId('lazy-image')).not.toBeInTheDocument();
  });

  it('renders image after intersection', async () => {
    render(<LazyImage src="/test.jpg" alt="Test image" />);

    simulateIntersection(true);

    await waitFor(() => {
      expect(screen.getByTestId('lazy-image')).toBeInTheDocument();
    });
  });

  it('applies correct alt text', async () => {
    render(<LazyImage src="/test.jpg" alt="Descriptive alt text" />);

    simulateIntersection(true);

    await waitFor(() => {
      const img = screen.getByTestId('lazy-image');
      expect(img).toHaveAttribute('alt', 'Descriptive alt text');
    });
  });

  it('applies srcSet and sizes when provided', async () => {
    const srcSet = '/test-400.jpg 400w, /test-800.jpg 800w';
    const sizes = '(max-width: 600px) 400px, 800px';

    render(
      <LazyImage
        src="/test.jpg"
        alt="Test"
        srcSet={srcSet}
        sizes={sizes}
      />
    );

    simulateIntersection(true);

    await waitFor(() => {
      const img = screen.getByTestId('lazy-image');
      expect(img).toHaveAttribute('srcSet', srcSet);
      expect(img).toHaveAttribute('sizes', sizes);
    });
  });

  it('renders placeholder when provided', async () => {
    render(
      <LazyImage
        src="/test.jpg"
        alt="Test"
        placeholder="/placeholder.jpg"
      />
    );

    expect(screen.getByTestId('lazy-image-placeholder')).toBeInTheDocument();
    expect(screen.getByTestId('lazy-image-placeholder')).toHaveAttribute('src', '/placeholder.jpg');
  });

  it('applies aspect ratio style', () => {
    render(
      <LazyImage
        src="/test.jpg"
        alt="Test"
        aspectRatio="16/9"
      />
    );

    const container = screen.getByTestId('lazy-image-container');
    expect(container).toHaveStyle({ aspectRatio: '16/9' });
  });

  it('applies custom className to image', async () => {
    render(
      <LazyImage
        src="/test.jpg"
        alt="Test"
        className="custom-image-class"
      />
    );

    simulateIntersection(true);

    await waitFor(() => {
      const img = screen.getByTestId('lazy-image');
      expect(img).toHaveClass('custom-image-class');
    });
  });

  it('applies containerClassName', () => {
    render(
      <LazyImage
        src="/test.jpg"
        alt="Test"
        containerClassName="custom-container-class"
      />
    );

    expect(screen.getByTestId('lazy-image-container')).toHaveClass('custom-container-class');
  });

  it('shows error fallback when image fails to load', async () => {
    render(<LazyImage src="/nonexistent.jpg" alt="Test" />);

    simulateIntersection(true);

    await waitFor(() => {
      const img = screen.getByTestId('lazy-image');
      // Simulate error event
      act(() => {
        img.dispatchEvent(new Event('error'));
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId('lazy-image-error')).toBeInTheDocument();
      expect(screen.getByText('Failed to load image')).toBeInTheDocument();
    });
  });

  it('renders custom error fallback', async () => {
    const customFallback = <div data-testid="custom-error">Custom error</div>;

    render(
      <LazyImage
        src="/nonexistent.jpg"
        alt="Test"
        errorFallback={customFallback}
      />
    );

    simulateIntersection(true);

    await waitFor(() => {
      const img = screen.getByTestId('lazy-image');
      act(() => {
        img.dispatchEvent(new Event('error'));
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId('custom-error')).toBeInTheDocument();
    });
  });

  it('calls onLoad callback when image loads', async () => {
    const handleLoad = vi.fn();

    render(<LazyImage src="/test.jpg" alt="Test" onLoad={handleLoad} />);

    simulateIntersection(true);

    await waitFor(() => {
      const img = screen.getByTestId('lazy-image');
      act(() => {
        img.dispatchEvent(new Event('load'));
      });
    });

    await waitFor(() => {
      expect(handleLoad).toHaveBeenCalledTimes(1);
    });
  });

  it('calls onError callback when image fails', async () => {
    const handleError = vi.fn();

    render(<LazyImage src="/test.jpg" alt="Test" onError={handleError} />);

    simulateIntersection(true);

    await waitFor(() => {
      const img = screen.getByTestId('lazy-image');
      act(() => {
        img.dispatchEvent(new Event('error'));
      });
    });

    await waitFor(() => {
      expect(handleError).toHaveBeenCalledTimes(1);
    });
  });

  it('hides skeleton when showSkeleton is false', () => {
    render(<LazyImage src="/test.jpg" alt="Test" showSkeleton={false} />);
    expect(screen.queryByTestId('lazy-image-skeleton')).not.toBeInTheDocument();
  });

  it('observes element with IntersectionObserver', () => {
    render(<LazyImage src="/test.jpg" alt="Test" />);
    expect(mockObserve).toHaveBeenCalled();
  });

  it('disconnects observer on unmount', () => {
    const { unmount } = render(<LazyImage src="/test.jpg" alt="Test" />);
    unmount();
    expect(mockDisconnect).toHaveBeenCalled();
  });

  it('passes through additional img attributes', async () => {
    render(
      <LazyImage
        src="/test.jpg"
        alt="Test"
        loading="lazy"
        decoding="async"
      />
    );

    simulateIntersection(true);

    await waitFor(() => {
      const img = screen.getByTestId('lazy-image');
      expect(img).toHaveAttribute('loading', 'lazy');
      expect(img).toHaveAttribute('decoding', 'async');
    });
  });
});

describe('LazyImage accessibility', () => {
  it('has appropriate alt text on main image', async () => {
    render(<LazyImage src="/test.jpg" alt="A beautiful landscape" />);

    simulateIntersection(true);

    await waitFor(() => {
      const img = screen.getByTestId('lazy-image');
      expect(img).toHaveAttribute('alt', 'A beautiful landscape');
    });
  });

  it('marks placeholder as decorative (aria-hidden)', () => {
    render(
      <LazyImage
        src="/test.jpg"
        alt="Test"
        placeholder="/placeholder.jpg"
      />
    );

    const placeholder = screen.getByTestId('lazy-image-placeholder');
    expect(placeholder).toHaveAttribute('aria-hidden', 'true');
    expect(placeholder).toHaveAttribute('alt', '');
  });
});
