import { describe, it, expect } from 'vitest';
import { render } from '@/test/test-utils';
import { PropertyCardSkeleton, PropertyCardSkeletonGrid } from './PropertyCardSkeleton';

describe('PropertyCardSkeleton', () => {
  it('renders with default structure', () => {
    const { container } = render(<PropertyCardSkeleton />);

    // Should have Card wrapper with overflow-hidden
    const card = container.querySelector('[class*="overflow-hidden"]');
    expect(card).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<PropertyCardSkeleton className="custom-property-class" />);

    const card = container.querySelector('.custom-property-class');
    expect(card).toBeInTheDocument();
  });

  it('renders image placeholder', () => {
    const { container } = render(<PropertyCardSkeleton />);

    // Image placeholder (h-48 w-full)
    const imagePlaceholder = container.querySelector('.h-48.w-full');
    expect(imagePlaceholder).toBeInTheDocument();
  });

  it('renders title and subtitle skeletons', () => {
    const { container } = render(<PropertyCardSkeleton />);

    // Title skeleton (h-6 w-3/4)
    const titleSkeleton = container.querySelector('.h-6.w-3\\/4');
    expect(titleSkeleton).toBeInTheDocument();

    // Subtitle skeleton (h-4 w-1/2)
    const subtitleSkeleton = container.querySelector('.h-4.w-1\\/2');
    expect(subtitleSkeleton).toBeInTheDocument();
  });

  it('renders 3 stat items', () => {
    const { container } = render(<PropertyCardSkeleton />);

    // Each stat has h-5 w-20 for the value
    const statValues = container.querySelectorAll('.h-5.w-20');
    expect(statValues.length).toBe(3);
  });

  it('renders badge placeholders', () => {
    const { container } = render(<PropertyCardSkeleton />);

    // Badge placeholders (rounded-full)
    const badges = container.querySelectorAll('.h-6.rounded-full');
    expect(badges.length).toBeGreaterThanOrEqual(2);
  });
});

describe('PropertyCardSkeletonGrid', () => {
  it('renders default 6 cards', () => {
    const { container } = render(<PropertyCardSkeletonGrid />);

    const cards = container.querySelectorAll('[class*="overflow-hidden"]');
    expect(cards.length).toBe(6);
  });

  it('renders custom count of cards', () => {
    const { container } = render(<PropertyCardSkeletonGrid count={4} />);

    const cards = container.querySelectorAll('[class*="overflow-hidden"]');
    expect(cards.length).toBe(4);
  });

  it('applies custom className to grid container', () => {
    const { container } = render(<PropertyCardSkeletonGrid className="custom-grid-class" />);

    const gridContainer = container.querySelector('.custom-grid-class');
    expect(gridContainer).toBeInTheDocument();
  });

  it('renders with grid layout classes', () => {
    const { container } = render(<PropertyCardSkeletonGrid />);

    const grid = container.firstElementChild;
    expect(grid?.classList.contains('grid')).toBe(true);
    expect(grid?.classList.contains('lg:grid-cols-3')).toBe(true);
  });

  it('renders responsive grid columns', () => {
    const { container } = render(<PropertyCardSkeletonGrid />);

    const grid = container.firstElementChild;
    expect(grid?.classList.contains('grid-cols-1')).toBe(true);
    expect(grid?.classList.contains('md:grid-cols-2')).toBe(true);
    expect(grid?.classList.contains('lg:grid-cols-3')).toBe(true);
  });
});
