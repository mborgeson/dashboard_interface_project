import { describe, it, expect } from 'vitest';
import { render } from '@/test/test-utils';
import { DealCardSkeleton, DealCardSkeletonList, DealPipelineSkeleton } from './DealCardSkeleton';

describe('DealCardSkeleton', () => {
  it('renders with default structure', () => {
    const { container } = render(<DealCardSkeleton />);

    // Should have Card wrapper
    const card = container.querySelector('[class*="overflow-hidden"]');
    expect(card).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<DealCardSkeleton className="custom-deal-class" />);

    const card = container.querySelector('.custom-deal-class');
    expect(card).toBeInTheDocument();
  });

  it('renders deal name and amount skeletons in header', () => {
    const { container } = render(<DealCardSkeleton />);

    // Deal name skeleton (h-5 w-3/4)
    const nameSkeleton = container.querySelector('.h-5.w-3\\/4');
    expect(nameSkeleton).toBeInTheDocument();

    // Amount skeleton (h-7 w-1/2)
    const amountSkeleton = container.querySelector('.h-7.w-1\\/2');
    expect(amountSkeleton).toBeInTheDocument();
  });

  it('renders status badges', () => {
    const { container } = render(<DealCardSkeleton />);

    // Status badges (rounded-full)
    const badges = container.querySelectorAll('.h-6.rounded-full');
    expect(badges.length).toBeGreaterThanOrEqual(2);
  });

  it('renders progress bar', () => {
    const { container } = render(<DealCardSkeleton />);

    // Progress bar (h-2 w-full rounded-full)
    const progressBar = container.querySelector('.h-2.w-full.rounded-full');
    expect(progressBar).toBeInTheDocument();
  });

  it('renders footer action buttons', () => {
    const { container } = render(<DealCardSkeleton />);

    // Footer buttons
    const buttons = container.querySelectorAll('.h-9');
    expect(buttons.length).toBeGreaterThanOrEqual(2);
  });
});

describe('DealCardSkeletonList', () => {
  it('renders default 3 cards', () => {
    const { container } = render(<DealCardSkeletonList />);

    const cards = container.querySelectorAll('[class*="overflow-hidden"]');
    expect(cards.length).toBe(3);
  });

  it('renders custom count of cards', () => {
    const { container } = render(<DealCardSkeletonList count={5} />);

    const cards = container.querySelectorAll('[class*="overflow-hidden"]');
    expect(cards.length).toBe(5);
  });

  it('applies custom className to list container', () => {
    const { container } = render(<DealCardSkeletonList className="custom-list-class" />);

    const listContainer = container.querySelector('.custom-list-class');
    expect(listContainer).toBeInTheDocument();
  });

  it('renders with space-y-4 class', () => {
    const { container } = render(<DealCardSkeletonList />);

    const listContainer = container.firstElementChild;
    expect(listContainer?.classList.contains('space-y-4')).toBe(true);
  });
});

describe('DealPipelineSkeleton', () => {
  it('renders 4 pipeline stages', () => {
    const { container } = render(<DealPipelineSkeleton />);

    // Should have 4 stage columns with space-y-4 class
    const stages = container.querySelectorAll('.space-y-4');
    // Each stage has space-y-4 (4 stage columns)
    expect(stages.length).toBeGreaterThanOrEqual(4);
  });

  it('applies custom className', () => {
    const { container } = render(<DealPipelineSkeleton className="custom-pipeline-class" />);

    const pipelineContainer = container.querySelector('.custom-pipeline-class');
    expect(pipelineContainer).toBeInTheDocument();
  });

  it('renders grid layout', () => {
    const { container } = render(<DealPipelineSkeleton />);

    const grid = container.querySelector('.grid');
    expect(grid).toBeInTheDocument();
    expect(grid?.classList.contains('lg:grid-cols-4')).toBe(true);
  });

  it('renders stage headers', () => {
    const { container } = render(<DealPipelineSkeleton />);

    // Stage headers (h-5 w-32) - one per stage
    const stageHeaders = container.querySelectorAll('.h-5.w-32');
    expect(stageHeaders.length).toBe(4);
  });

  it('renders deal cards within stages', () => {
    const { container } = render(<DealPipelineSkeleton />);

    // Should have deal cards with p-4 class
    const dealCards = container.querySelectorAll('.p-4');
    // Sum of STAGE_CARD_COUNTS = 2 + 3 + 1 + 2 = 8
    expect(dealCards.length).toBe(8);
  });
});
