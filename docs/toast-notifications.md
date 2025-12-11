# Toast Notifications System

Complete toast notification system for the B&R Capital Real Estate Analytics Dashboard.

## Overview

The toast notification system provides:
- **Toast Notifications**: Temporary pop-up messages (bottom-right corner)
- **Alert Banners**: Full-width page-level alerts
- **Type Safety**: Full TypeScript support
- **Auto-dismiss**: Configurable duration with progress bar
- **Action Buttons**: Optional action buttons in toasts
- **Animations**: Smooth slide-in/out animations
- **Dark Mode**: Full dark mode support
- **Accessibility**: ARIA labels and keyboard support

## Architecture

### Components

```
src/
├── types/notification.ts           # Type definitions
├── stores/notificationStore.ts     # Zustand store
├── contexts/ToastContext.tsx       # Provider component
├── hooks/useToast.ts               # Convenience hook
└── components/ui/
    ├── toast.tsx                   # Individual toast
    ├── toast-container.tsx         # Portal container
    ├── alert-banner.tsx            # Page-level alerts
    └── toast-demo.tsx              # Usage examples
```

### Flow

1. **Store**: Zustand store manages toast state
2. **Provider**: ToastProvider wraps app and renders ToastContainer
3. **Container**: Renders toasts via portal to document.body
4. **Hook**: useToast() provides convenience methods
5. **Auto-dismiss**: Timers automatically remove toasts

## Usage

### Basic Toast Notifications

```typescript
import { useToast } from '@/hooks/useToast';

function MyComponent() {
  const { success, error, warning, info } = useToast();

  const handleSave = async () => {
    try {
      await saveProperty(data);
      success('Property saved successfully');
    } catch (err) {
      error('Failed to save property');
    }
  };

  return <button onClick={handleSave}>Save</button>;
}
```

### Toast with Description

```typescript
error('Upload failed', {
  description: 'File size exceeds 10MB limit'
});

warning('Unsaved changes', {
  description: 'You have unsaved changes that will be lost'
});
```

### Toast with Action Button

```typescript
import { useNavigate } from 'react-router-dom';

const navigate = useNavigate();

success('Deal created successfully', {
  action: {
    label: 'View Deal',
    onClick: () => navigate('/deals/123')
  }
});

info('New update available', {
  action: {
    label: 'Refresh',
    onClick: () => window.location.reload()
  }
});
```

### Custom Duration

```typescript
// Default: 5000ms (5 seconds)
success('Quick message'); 

// Custom duration
warning('Important notice', { duration: 10000 }); // 10 seconds

// No auto-dismiss (duration: 0)
const id = info('Processing...', { duration: 0 });

// Manually dismiss later
setTimeout(() => dismiss(id), 5000);
```

### Manual Dismiss

```typescript
const { info, success, dismiss } = useToast();

const handleProcess = async () => {
  const id = info('Processing documents...', { duration: 0 });
  
  try {
    await processDocuments();
    dismiss(id); // Remove the processing toast
    success('Documents processed successfully');
  } catch (err) {
    dismiss(id);
    error('Processing failed');
  }
};
```

### Advanced Toast API

```typescript
import { useToast } from '@/hooks/useToast';

const { toast } = useToast();

// Full control with toast() function
toast({
  type: 'success',
  title: 'Custom notification',
  description: 'With full options',
  duration: 7000,
  action: {
    label: 'Action',
    onClick: () => console.log('clicked')
  }
});
```

## Alert Banners

Full-width page-level alerts that remain visible until dismissed.

### Basic Alert

```typescript
import { AlertBanner } from '@/components/ui';

<AlertBanner
  variant="success"
  title="Property saved"
  description="All changes have been saved successfully."
/>
```

### Dismissible Alert

```typescript
import { AlertBanner } from '@/components/ui';
import { useState } from 'react';

function MyPage() {
  const [showAlert, setShowAlert] = useState(true);

  if (!showAlert) return null;

  return (
    <AlertBanner
      variant="info"
      title="New features available"
      description="Check out the new analytics dashboard."
      dismissible
      onDismiss={() => setShowAlert(false)}
    />
  );
}
```

### Alert with Action

```typescript
<AlertBanner
  variant="warning"
  title="Payment method expiring"
  description="Your credit card expires next month."
  dismissible
  action={{
    label: 'Update Payment',
    onClick: () => navigate('/settings/billing')
  }}
/>
```

## Toast Types & Colors

| Type | Icon | Colors |
|------|------|--------|
| `success` | CheckCircle | Green |
| `error` | XCircle | Red |
| `warning` | AlertTriangle | Amber |
| `info` | Info | Blue |

## API Reference

### useToast Hook

```typescript
interface UseToastReturn {
  toast: (options: ToastOptions) => string;
  success: (title: string, options?: Omit<ToastOptions, 'type' | 'title'>) => string;
  error: (title: string, options?: Omit<ToastOptions, 'type' | 'title'>) => string;
  warning: (title: string, options?: Omit<ToastOptions, 'type' | 'title'>) => string;
  info: (title: string, options?: Omit<ToastOptions, 'type' | 'title'>) => string;
  dismiss: (id: string) => void;
}
```

### Toast Options

```typescript
interface ToastOptions {
  id?: string;                // Optional custom ID
  type: ToastType;            // 'success' | 'error' | 'warning' | 'info'
  title: string;              // Main message
  description?: string;       // Optional additional text
  duration?: number;          // ms, default 5000, 0 = no auto-dismiss
  action?: {                  // Optional action button
    label: string;
    onClick: () => void;
  };
}
```

### Alert Banner Props

```typescript
interface AlertBannerProps {
  variant: ToastType;         // 'success' | 'error' | 'warning' | 'info'
  title: string;              // Main message
  description?: string;       // Optional additional text
  dismissible?: boolean;      // Show close button
  action?: {                  // Optional action button
    label: string;
    onClick: () => void;
  };
  onDismiss?: () => void;     // Callback when dismissed
}
```

## Common Patterns

### Form Submission

```typescript
const handleSubmit = async (data: FormData) => {
  try {
    await submitForm(data);
    success('Form submitted successfully');
    navigate('/success');
  } catch (err) {
    error('Submission failed', {
      description: err.message
    });
  }
};
```

### File Upload

```typescript
const handleUpload = async (file: File) => {
  if (file.size > 10 * 1024 * 1024) {
    error('Upload failed', {
      description: 'File size exceeds 10MB limit'
    });
    return;
  }

  const id = info('Uploading...', { duration: 0 });
  
  try {
    await uploadFile(file);
    dismiss(id);
    success('File uploaded successfully', {
      action: {
        label: 'View',
        onClick: () => navigate('/documents')
      }
    });
  } catch (err) {
    dismiss(id);
    error('Upload failed', {
      description: 'Please try again or contact support'
    });
  }
};
```

### Async Operations

```typescript
const handleDelete = async (id: string) => {
  const toastId = warning('Deleting property...', { duration: 0 });
  
  try {
    await deleteProperty(id);
    dismiss(toastId);
    success('Property deleted successfully');
    refreshList();
  } catch (err) {
    dismiss(toastId);
    error('Delete failed', {
      description: 'The property could not be deleted',
      action: {
        label: 'Retry',
        onClick: () => handleDelete(id)
      }
    });
  }
};
```

### Multiple Operations

```typescript
const handleBulkAction = async (items: string[]) => {
  const results = await Promise.allSettled(
    items.map(id => processItem(id))
  );
  
  const succeeded = results.filter(r => r.status === 'fulfilled').length;
  const failed = results.filter(r => r.status === 'rejected').length;
  
  if (succeeded > 0) {
    success(`${succeeded} items processed successfully`);
  }
  
  if (failed > 0) {
    error(`${failed} items failed`, {
      description: 'Some items could not be processed',
      action: {
        label: 'View Details',
        onClick: () => showErrorDetails(results)
      }
    });
  }
};
```

## Styling

### Color Scheme

All colors support both light and dark modes:

```typescript
// Success (Green)
bg-green-50 dark:bg-green-950
border-green-500
text-green-500

// Error (Red)
bg-red-50 dark:bg-red-950
border-red-500
text-red-500

// Warning (Amber)
bg-amber-50 dark:bg-amber-950
border-amber-500
text-amber-500

// Info (Blue)
bg-blue-50 dark:bg-blue-950
border-blue-500
text-blue-500
```

### Customization

To customize toast appearance, edit:
- `src/components/ui/toast.tsx` - Individual toast styling
- `src/components/ui/toast-container.tsx` - Container positioning
- `src/components/ui/alert-banner.tsx` - Banner styling

## Best Practices

### Do's

✅ Use appropriate toast types for the context
✅ Keep titles concise (< 50 characters)
✅ Add descriptions for complex errors
✅ Provide action buttons for important notifications
✅ Use persistent toasts (duration: 0) for critical info
✅ Dismiss programmatically when operations complete

### Don'ts

❌ Don't show too many toasts at once (max 5 visible)
❌ Don't use toasts for critical errors (use modals)
❌ Don't make success toasts too verbose
❌ Don't forget to dismiss persistent toasts
❌ Don't use toasts for information that users need to reference later

## Testing

### Demo Component

Use the demo component to test all features:

```typescript
import { ToastDemo } from '@/components/ui/toast-demo';

// In your route config
{
  path: '/demo/toasts',
  element: <ToastDemo />
}
```

### Manual Testing Checklist

- [ ] Success toast displays with green styling
- [ ] Error toast displays with red styling
- [ ] Warning toast displays with amber styling
- [ ] Info toast displays with blue styling
- [ ] Toast auto-dismisses after duration
- [ ] Progress bar animates correctly
- [ ] Close button removes toast immediately
- [ ] Action button triggers callback
- [ ] Multiple toasts stack correctly (max 5)
- [ ] Toasts animate in from right
- [ ] Toasts animate out when dismissed
- [ ] Alert banners display full-width
- [ ] Dismissible banners can be closed
- [ ] Dark mode styling works correctly

## Troubleshooting

### Toast Not Appearing

1. Verify ToastProvider wraps your app in `src/app/App.tsx`
2. Check that you're calling the hook inside a component
3. Ensure the toast isn't being dismissed too quickly

### Multiple Toasts Not Showing

- Container shows max 5 toasts (by design)
- Older toasts are automatically removed

### TypeScript Errors

- Run `npx tsc --noEmit` to check for type errors
- Ensure all imports use correct paths with `@/` prefix

### Styling Issues

- Verify Tailwind CSS is configured correctly
- Check that dark mode classes are properly applied
- Ensure z-index (9999) doesn't conflict with other elements

## Future Enhancements

Potential improvements:
- [ ] Toast positioning options (top/bottom, left/right)
- [ ] Custom toast icons
- [ ] Sound notifications
- [ ] Toast groups/categories
- [ ] Undo functionality
- [ ] Persistent toast history
- [ ] Toast templates for common patterns
