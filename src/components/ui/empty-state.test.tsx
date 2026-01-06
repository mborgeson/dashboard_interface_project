import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import {
  EmptyState,
  CompactEmptyState,
  TableEmptyState,
  EmptyInvestments,
  EmptyTransactions,
  EmptyDocuments,
  EmptyDeals,
} from './empty-state';

describe('EmptyState', () => {
  it('renders with title', () => {
    render(<EmptyState title="No Items" />);

    expect(screen.getByText('No Items')).toBeInTheDocument();
  });

  it('renders with description', () => {
    render(
      <EmptyState
        title="No Items"
        description="There are no items to display"
      />
    );

    expect(screen.getByText('There are no items to display')).toBeInTheDocument();
  });

  it('renders action button when action is provided', async () => {
    const user = userEvent.setup();
    const mockAction = vi.fn();

    render(
      <EmptyState
        title="No Items"
        action={{ label: 'Add Item', onClick: mockAction }}
      />
    );

    const button = screen.getByRole('button', { name: /add item/i });
    expect(button).toBeInTheDocument();

    await user.click(button);
    expect(mockAction).toHaveBeenCalledTimes(1);
  });

  it('renders action button with custom variant', () => {
    render(
      <EmptyState
        title="No Items"
        action={{ label: 'Add', onClick: () => {}, variant: 'outline' }}
      />
    );

    const button = screen.getByRole('button');
    expect(button).toHaveClass('border');
  });

  it('does not render action button when action is not provided', () => {
    render(<EmptyState title="No Items" />);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <EmptyState title="No Items" className="custom-empty-class" />
    );

    expect(container.querySelector('.custom-empty-class')).toBeInTheDocument();
  });

  it('applies custom iconClassName', () => {
    const { container } = render(
      <EmptyState title="No Items" iconClassName="custom-icon-class" />
    );

    expect(container.querySelector('.custom-icon-class')).toBeInTheDocument();
  });

  it('renders with dashed border', () => {
    const { container } = render(<EmptyState title="No Items" />);

    expect(container.querySelector('.border-dashed')).toBeInTheDocument();
  });
});

describe('CompactEmptyState', () => {
  it('renders with title', () => {
    render(<CompactEmptyState title="Empty" />);

    expect(screen.getByText('Empty')).toBeInTheDocument();
  });

  it('renders with description', () => {
    render(
      <CompactEmptyState
        title="Empty"
        description="No data available"
      />
    );

    expect(screen.getByText('No data available')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <CompactEmptyState title="Empty" className="custom-compact-class" />
    );

    expect(container.querySelector('.custom-compact-class')).toBeInTheDocument();
  });

  it('has centered layout', () => {
    const { container } = render(<CompactEmptyState title="Empty" />);

    expect(container.querySelector('.items-center.justify-center')).toBeInTheDocument();
  });
});

describe('TableEmptyState', () => {
  it('renders default no data message', () => {
    render(<TableEmptyState />);

    expect(screen.getByText('No data available')).toBeInTheDocument();
    expect(screen.getByText('There are no items to display at this time.')).toBeInTheDocument();
  });

  it('renders search-specific message when searchTerm is provided', () => {
    render(<TableEmptyState searchTerm="test query" />);

    expect(screen.getByText('No results found')).toBeInTheDocument();
    expect(screen.getByText(/no items match "test query"/i)).toBeInTheDocument();
  });

  it('renders clear search button when searchTerm and onClearSearch are provided', async () => {
    const user = userEvent.setup();
    const mockClear = vi.fn();

    render(<TableEmptyState searchTerm="test" onClearSearch={mockClear} />);

    const clearButton = screen.getByRole('button', { name: /clear search/i });
    expect(clearButton).toBeInTheDocument();

    await user.click(clearButton);
    expect(mockClear).toHaveBeenCalledTimes(1);
  });

  it('does not render clear button without onClearSearch', () => {
    render(<TableEmptyState searchTerm="test" />);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <TableEmptyState className="custom-table-empty-class" />
    );

    expect(container.querySelector('.custom-table-empty-class')).toBeInTheDocument();
  });
});

describe('EmptyInvestments', () => {
  it('renders correct title and description', () => {
    render(<EmptyInvestments />);

    expect(screen.getByText('No properties yet')).toBeInTheDocument();
    expect(screen.getByText(/start building your real estate portfolio/i)).toBeInTheDocument();
  });

  it('renders add button when onAdd is provided', async () => {
    const user = userEvent.setup();
    const mockAdd = vi.fn();

    render(<EmptyInvestments onAdd={mockAdd} />);

    const addButton = screen.getByRole('button', { name: /add property/i });
    await user.click(addButton);

    expect(mockAdd).toHaveBeenCalledTimes(1);
  });
});

describe('EmptyTransactions', () => {
  it('renders correct title and description', () => {
    render(<EmptyTransactions />);

    expect(screen.getByText('No transactions')).toBeInTheDocument();
    expect(screen.getByText(/transaction history will appear/i)).toBeInTheDocument();
  });

  it('does not render action button', () => {
    render(<EmptyTransactions />);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});

describe('EmptyDocuments', () => {
  it('renders correct title and description', () => {
    render(<EmptyDocuments />);

    expect(screen.getByText('No documents')).toBeInTheDocument();
    expect(screen.getByText(/upload important documents/i)).toBeInTheDocument();
  });

  it('renders upload button when onUpload is provided', async () => {
    const user = userEvent.setup();
    const mockUpload = vi.fn();

    render(<EmptyDocuments onUpload={mockUpload} />);

    const uploadButton = screen.getByRole('button', { name: /upload document/i });
    await user.click(uploadButton);

    expect(mockUpload).toHaveBeenCalledTimes(1);
  });
});

describe('EmptyDeals', () => {
  it('renders correct title and description', () => {
    render(<EmptyDeals />);

    expect(screen.getByText('No deals in pipeline')).toBeInTheDocument();
    expect(screen.getByText(/track potential investment opportunities/i)).toBeInTheDocument();
  });

  it('renders add button when onAdd is provided', async () => {
    const user = userEvent.setup();
    const mockAdd = vi.fn();

    render(<EmptyDeals onAdd={mockAdd} />);

    const addButton = screen.getByRole('button', { name: /add deal/i });
    await user.click(addButton);

    expect(mockAdd).toHaveBeenCalledTimes(1);
  });
});
