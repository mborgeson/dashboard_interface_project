import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { GroupPipelineStepper } from '../GroupPipelineStepper';
import type { PipelineStatus } from '@/types/grouping';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const PHASE_LABELS = [
  'Discovery',
  'Fingerprint & Group',
  'Reference Map',
  'Conflict Check',
  'Extract',
  'Validate',
];

function makeStatus(phaseOverrides: Record<string, string> = {}): PipelineStatus {
  return {
    data_dir: '/data/uw-models',
    phases: phaseOverrides,
    stats: { total_files: 100 },
    created_at: '2026-03-01T09:00:00Z',
    updated_at: '2026-03-01T09:00:00Z',
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('GroupPipelineStepper', () => {
  describe('phase labels', () => {
    it('renders all 6 phase labels', () => {
      const status = makeStatus();
      render(<GroupPipelineStepper status={status} isLoading={false} />);

      for (const label of PHASE_LABELS) {
        expect(screen.getByText(label)).toBeInTheDocument();
      }
    });
  });

  describe('loading state', () => {
    it('shows skeleton pulses when isLoading is true', () => {
      const { container } = render(
        <GroupPipelineStepper status={null} isLoading={true} />,
      );

      const pulses = container.querySelectorAll('.animate-pulse');
      // 6 circles should have pulse animation
      expect(pulses.length).toBe(6);
    });

    it('does not show phase labels when loading', () => {
      render(<GroupPipelineStepper status={null} isLoading={true} />);

      for (const label of PHASE_LABELS) {
        expect(screen.queryByText(label)).not.toBeInTheDocument();
      }
    });
  });

  describe('completed phases', () => {
    it('shows green styling for phases with timestamps', () => {
      const status = makeStatus({
        discovery: '2026-03-01T10:00:00Z',
        fingerprint: '2026-03-01T10:30:00Z',
      });

      const { container } = render(
        <GroupPipelineStepper status={status} isLoading={false} />,
      );

      // Completed phases get green text
      const greenLabels = container.querySelectorAll('.text-green-700');
      expect(greenLabels.length).toBe(2);
    });

    it('displays formatted timestamps for completed phases', () => {
      const status = makeStatus({
        discovery: '2026-03-01T10:00:00Z',
      });

      render(<GroupPipelineStepper status={status} isLoading={false} />);

      // The component formats timestamps with month, day, hour, minute
      // Exact format depends on locale, but a timestamp element should be present
      const timestampElements = document.querySelectorAll('.text-\\[10px\\]');
      expect(timestampElements.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('pending phases', () => {
    it('shows gray styling for phases without timestamps', () => {
      const status = makeStatus({}); // No phases completed

      const { container } = render(
        <GroupPipelineStepper status={status} isLoading={false} />,
      );

      // All phases except the first (which is "current") should be pending/gray
      const grayLabels = container.querySelectorAll('.text-neutral-400');
      // 5 pending phases have gray label text
      expect(grayLabels.length).toBeGreaterThanOrEqual(5);
    });
  });

  describe('current phase', () => {
    it('shows blue styling for the first incomplete phase after a completed one', () => {
      const status = makeStatus({
        discovery: '2026-03-01T10:00:00Z',
      });

      const { container } = render(
        <GroupPipelineStepper status={status} isLoading={false} />,
      );

      // "Fingerprint & Group" should be the current (blue) phase
      const blueLabels = container.querySelectorAll('.text-blue-700');
      expect(blueLabels.length).toBe(1);
    });

    it('marks the first phase as current when no phases are completed', () => {
      const status = makeStatus({});

      const { container } = render(
        <GroupPipelineStepper status={status} isLoading={false} />,
      );

      // Discovery should be current (blue)
      const blueLabels = container.querySelectorAll('.text-blue-700');
      expect(blueLabels.length).toBe(1);
    });
  });

  describe('null status', () => {
    it('handles null status gracefully by rendering all phases as pending', () => {
      render(<GroupPipelineStepper status={null} isLoading={false} />);

      // All labels should still render
      for (const label of PHASE_LABELS) {
        expect(screen.getByText(label)).toBeInTheDocument();
      }
    });

    it('does not crash when status is null and isLoading is false', () => {
      const { container } = render(
        <GroupPipelineStepper status={null} isLoading={false} />,
      );

      // No green (completed) labels
      const greenLabels = container.querySelectorAll('.text-green-700');
      expect(greenLabels.length).toBe(0);
    });
  });

  describe('all phases completed', () => {
    it('shows all phases as green when all have timestamps', () => {
      const status = makeStatus({
        discovery: '2026-03-01T10:00:00Z',
        fingerprint: '2026-03-01T10:30:00Z',
        reference_map: '2026-03-01T11:00:00Z',
        conflict_check: '2026-03-01T11:30:00Z',
        extract: '2026-03-01T12:00:00Z',
        validate: '2026-03-01T12:30:00Z',
      });

      const { container } = render(
        <GroupPipelineStepper status={status} isLoading={false} />,
      );

      const greenLabels = container.querySelectorAll('.text-green-700');
      expect(greenLabels.length).toBe(6);

      // No blue (current) labels
      const blueLabels = container.querySelectorAll('.text-blue-700');
      expect(blueLabels.length).toBe(0);
    });
  });

  describe('connector lines', () => {
    it('renders 5 connector lines between 6 phases', () => {
      const status = makeStatus();
      const { container } = render(
        <GroupPipelineStepper status={status} isLoading={false} />,
      );

      // Connector divs have h-0.5 class
      const connectors = container.querySelectorAll('.h-0\\.5');
      expect(connectors.length).toBe(5);
    });
  });
});
