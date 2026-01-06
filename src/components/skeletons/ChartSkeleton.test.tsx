import { describe, it, expect } from "vitest";
import { render, screen } from "@/test/test-utils";
import {
  ChartSkeleton,
  ChartCardSkeleton,
  LineChartSkeleton,
} from "./ChartSkeleton";

describe("ChartSkeleton", () => {
  it("renders with default props", () => {
    render(<ChartSkeleton />);

    // Should have chart bars
    const container = document.querySelector(".space-y-3");
    expect(container).toBeInTheDocument();
  });

  it("renders title skeleton when showTitle is true", () => {
    render(<ChartSkeleton showTitle={true} />);

    // Title skeleton should be present (h-6 w-1/4 class)
    const titleSkeleton = document.querySelector(".h-6.w-1\\/4");
    expect(titleSkeleton).toBeInTheDocument();
  });

  it("hides title skeleton when showTitle is false", () => {
    const { container } = render(<ChartSkeleton showTitle={false} />);

    // Should not have the title skeleton as first child
    const spaceContainer = container.querySelector(".space-y-3");
    const firstChild = spaceContainer?.firstElementChild;
    expect(firstChild?.classList.contains("h-6")).toBe(false);
  });

  it("renders legend when showLegend is true", () => {
    render(<ChartSkeleton showLegend={true} />);

    // Legend container should have flex and justify-center
    const legendContainer = document.querySelector(
      ".flex.gap-4.justify-center"
    );
    expect(legendContainer).toBeInTheDocument();
  });

  it("hides legend when showLegend is false", () => {
    render(<ChartSkeleton showLegend={false} />);

    // Legend container should not be present
    const legendContainer = document.querySelector(
      ".flex.gap-4.justify-center.flex-wrap"
    );
    expect(legendContainer).not.toBeInTheDocument();
  });

  it("applies custom height", () => {
    render(<ChartSkeleton height={400} />);

    // Chart area should have custom height
    const chartArea = document.querySelector('[style*="height: 400px"]');
    expect(chartArea).toBeInTheDocument();
  });

  it("applies custom className", () => {
    render(<ChartSkeleton className="custom-class" />);

    const container = document.querySelector(".custom-class");
    expect(container).toBeInTheDocument();
  });

  it('renders 8 chart bars', () => {
    const { container } = render(<ChartSkeleton />);

    // Should have 8 bar skeletons in the chart area (items-end container)
    const barsContainer = container.querySelector('.items-end');
    const bars = barsContainer?.querySelectorAll('.animate-pulse');
    expect(bars?.length).toBe(8);
  });

  it("renders 4 legend items when showLegend is true", () => {
    render(<ChartSkeleton showLegend={true} />);

    // Should have 4 legend items (each with a circle and text skeleton)
    const legendCircles = document.querySelectorAll(".h-3.w-3.rounded-full");
    expect(legendCircles.length).toBe(4);
  });
});

describe("ChartCardSkeleton", () => {
  it("renders with card wrapper", () => {
    render(<ChartCardSkeleton />);

    // Should have Card component (with CardHeader and CardContent)
    const card = document.querySelector('[class*="border"]');
    expect(card).toBeInTheDocument();
  });

  it("applies custom className", () => {
    render(<ChartCardSkeleton className="custom-card-class" />);

    const card = document.querySelector(".custom-card-class");
    expect(card).toBeInTheDocument();
  });

  it("renders ChartSkeleton without title inside card", () => {
    render(<ChartCardSkeleton />);

    // The inner ChartSkeleton should have showTitle={false}
    // Card header has its own title skeleton
    const headerTitleSkeleton = document.querySelector(".h-6.w-1\\/3");
    expect(headerTitleSkeleton).toBeInTheDocument();
  });
});

describe("LineChartSkeleton", () => {
  it("renders with default layout", () => {
    render(<LineChartSkeleton />);

    // Should have space-y-3 container
    const container = document.querySelector(".space-y-3");
    expect(container).toBeInTheDocument();
  });

  it("renders SVG with line paths", () => {
    render(<LineChartSkeleton />);

    // Should have SVG element with polylines
    const svg = document.querySelector("svg");
    expect(svg).toBeInTheDocument();

    const polylines = document.querySelectorAll("polyline");
    expect(polylines.length).toBe(2);
  });

  it("renders gradient definition", () => {
    render(<LineChartSkeleton />);

    // Should have linearGradient with id="shimmer"
    const gradient = document.querySelector("#shimmer");
    expect(gradient).toBeInTheDocument();
  });

  it("applies custom className", () => {
    render(<LineChartSkeleton className="custom-line-class" />);

    const container = document.querySelector(".custom-line-class");
    expect(container).toBeInTheDocument();
  });

  it("renders 3 legend items", () => {
    render(<LineChartSkeleton />);

    // Should have 3 legend items
    const legendCircles = document.querySelectorAll(".h-3.w-3.rounded-full");
    expect(legendCircles.length).toBe(3);
  });
});
