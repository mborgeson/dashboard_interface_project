import { describe, it, expect } from 'vitest';
import { render } from '@/test/test-utils';
import { StatCardSkeleton, StatCardSkeletonGrid, MiniStatSkeleton } from './StatCardSkeleton';

describe('StatCardSkeleton', () => {
  describe('horizontal orientation (default)', () => {
    it('renders with default structure', () => {
      const { container } = render(<StatCardSkeleton />);

      // Should have Card wrapper
      const card = container.querySelector('[class*="border"]');
      expect(card).toBeInTheDocument();
    });

    it('applies custom className', () => {
      const { container } = render(<StatCardSkeleton className="custom-stat-class" />);

      const card = container.querySelector('.custom-stat-class');
      expect(card).toBeInTheDocument();
    });

    it('renders label skeleton', () => {
      const { container } = render(<StatCardSkeleton />);

      // Label skeleton (h-4 w-32)
      const labelSkeleton = container.querySelector('.h-4.w-32');
      expect(labelSkeleton).toBeInTheDocument();
    });

    it('renders value skeleton', () => {
      const { container } = render(<StatCardSkeleton />);

      // Value skeleton (h-8 w-24)
      const valueSkeleton = container.querySelector('.h-8.w-24');
      expect(valueSkeleton).toBeInTheDocument();
    });

    it('renders icon placeholder', () => {
      const { container } = render(<StatCardSkeleton />);

      // Icon placeholder (h-12 w-12 rounded-lg)
      const iconPlaceholder = container.querySelector('.h-12.w-12.rounded-lg');
      expect(iconPlaceholder).toBeInTheDocument();
    });

    it('renders trend indicator', () => {
      const { container } = render(<StatCardSkeleton />);

      // Trend circle (h-4 w-4 rounded-full)
      const trendCircle = container.querySelector('.h-4.w-4.rounded-full');
      expect(trendCircle).toBeInTheDocument();
    });
  });

  describe('vertical orientation', () => {
    it('renders with vertical layout', () => {
      const { container } = render(<StatCardSkeleton orientation="vertical" />);

      // Should have space-y-4 in CardContent for vertical
      const contentWithSpacing = container.querySelector('.space-y-4');
      expect(contentWithSpacing).toBeInTheDocument();
    });

    it('renders icon first in vertical layout', () => {
      const { container } = render(<StatCardSkeleton orientation="vertical" />);

      // Icon placeholder (h-12 w-12 rounded-lg) should be present
      const iconPlaceholder = container.querySelector('.h-12.w-12.rounded-lg');
      expect(iconPlaceholder).toBeInTheDocument();
    });
  });
});

describe('StatCardSkeletonGrid', () => {
  it('renders default 4 cards', () => {
    const { container } = render(<StatCardSkeletonGrid />);

    // Each card has CardContent with pt-6
    const cards = container.querySelectorAll('.pt-6');
    expect(cards.length).toBe(4);
  });

  it('renders custom count of cards', () => {
    const { container } = render(<StatCardSkeletonGrid count={6} />);

    const cards = container.querySelectorAll('.pt-6');
    expect(cards.length).toBe(6);
  });

  it('applies custom className to grid container', () => {
    const { container } = render(<StatCardSkeletonGrid className="custom-grid-class" />);

    const gridContainer = container.querySelector('.custom-grid-class');
    expect(gridContainer).toBeInTheDocument();
  });

  it('renders with grid layout classes', () => {
    const { container } = render(<StatCardSkeletonGrid />);

    const grid = container.firstElementChild;
    expect(grid?.classList.contains('grid')).toBe(true);
    expect(grid?.classList.contains('lg:grid-cols-4')).toBe(true);
  });

  it('passes orientation to child cards', () => {
    const { container } = render(<StatCardSkeletonGrid orientation="vertical" />);

    // Vertical layout has space-y-4 in CardContent
    const verticalLayouts = container.querySelectorAll('.space-y-4');
    expect(verticalLayouts.length).toBe(4);
  });
});

describe('MiniStatSkeleton', () => {
  it('renders with default structure', () => {
    const { container } = render(<MiniStatSkeleton />);

    // Should have flex layout
    const flexContainer = container.querySelector('.flex.items-center.gap-3');
    expect(flexContainer).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<MiniStatSkeleton className="custom-mini-class" />);

    const miniStat = container.querySelector('.custom-mini-class');
    expect(miniStat).toBeInTheDocument();
  });

  it('renders circular avatar placeholder', () => {
    const { container } = render(<MiniStatSkeleton />);

    // Avatar placeholder (h-10 w-10 rounded-full)
    const avatar = container.querySelector('.h-10.w-10.rounded-full');
    expect(avatar).toBeInTheDocument();
  });

  it('renders value and label skeletons', () => {
    const { container } = render(<MiniStatSkeleton />);

    // Value skeleton (h-6 w-20)
    const valueSkeleton = container.querySelector('.h-6.w-20');
    expect(valueSkeleton).toBeInTheDocument();

    // Label skeleton (h-3 w-24)
    const labelSkeleton = container.querySelector('.h-3.w-24');
    expect(labelSkeleton).toBeInTheDocument();
  });
});
