import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from './card';

describe('Card Components', () => {
  describe('Card', () => {
    it('renders children correctly', () => {
      render(<Card>Card content</Card>);
      expect(screen.getByText('Card content')).toBeInTheDocument();
    });

    it('applies base styles', () => {
      render(<Card data-testid="card">Content</Card>);
      const card = screen.getByTestId('card');
      expect(card).toHaveClass('rounded-lg', 'border', 'bg-card');
    });

    it('accepts custom className', () => {
      render(<Card className="custom-card" data-testid="card">Content</Card>);
      const card = screen.getByTestId('card');
      expect(card).toHaveClass('custom-card');
    });
  });

  describe('CardHeader', () => {
    it('renders with correct spacing', () => {
      render(<CardHeader data-testid="header">Header</CardHeader>);
      const header = screen.getByTestId('header');
      expect(header).toHaveClass('flex', 'flex-col', 'space-y-1.5', 'p-6');
    });
  });

  describe('CardTitle', () => {
    it('renders with correct styles', () => {
      render(<CardTitle data-testid="title">Title</CardTitle>);
      const title = screen.getByTestId('title');
      expect(title).toHaveTextContent('Title');
      expect(title).toHaveClass('text-2xl', 'font-semibold');
    });
  });

  describe('CardDescription', () => {
    it('renders with muted text color', () => {
      render(<CardDescription data-testid="desc">Description</CardDescription>);
      const desc = screen.getByTestId('desc');
      expect(desc).toHaveClass('text-sm', 'text-muted-foreground');
    });
  });

  describe('CardContent', () => {
    it('renders with correct padding', () => {
      render(<CardContent data-testid="content">Content</CardContent>);
      const content = screen.getByTestId('content');
      expect(content).toHaveClass('p-6', 'pt-0');
    });
  });

  describe('CardFooter', () => {
    it('renders with flex layout', () => {
      render(<CardFooter data-testid="footer">Footer</CardFooter>);
      const footer = screen.getByTestId('footer');
      expect(footer).toHaveClass('flex', 'items-center', 'p-6', 'pt-0');
    });
  });

  describe('Full Card Composition', () => {
    it('renders complete card structure', () => {
      render(
        <Card data-testid="full-card">
          <CardHeader>
            <CardTitle data-testid="card-title">Test Card</CardTitle>
            <CardDescription>This is a test card</CardDescription>
          </CardHeader>
          <CardContent>Card body content</CardContent>
          <CardFooter>Card footer</CardFooter>
        </Card>
      );

      expect(screen.getByTestId('full-card')).toBeInTheDocument();
      expect(screen.getByTestId('card-title')).toHaveTextContent('Test Card');
      expect(screen.getByText('This is a test card')).toBeInTheDocument();
      expect(screen.getByText('Card body content')).toBeInTheDocument();
      expect(screen.getByText('Card footer')).toBeInTheDocument();
    });
  });
});
