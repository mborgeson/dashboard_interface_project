# Toast Notifications - Quick Start Guide

## Installation ✓

**Already integrated!** No installation needed. The toast system is ready to use.

## 1. Basic Usage (Copy & Paste)

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

## 2. Common Patterns

### Form Submission
```typescript
const handleSubmit = async (data) => {
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
const handleUpload = async (file) => {
  const id = info('Uploading...', { duration: 0 });
  
  try {
    await uploadFile(file);
    dismiss(id);
    success('File uploaded successfully');
  } catch (err) {
    dismiss(id);
    error('Upload failed');
  }
};
```

### With Action Button
```typescript
success('Deal created', {
  action: {
    label: 'View Deal',
    onClick: () => navigate('/deals/123')
  }
});
```

## 3. Alert Banners (Page-Level)

```typescript
import { AlertBanner } from '@/components/ui';

<AlertBanner
  variant="warning"
  title="Payment method expiring"
  description="Your card expires next month"
  dismissible
  action={{
    label: 'Update',
    onClick: () => navigate('/settings')
  }}
/>
```

## 4. Toast Types

| Method | Use For | Example |
|--------|---------|---------|
| `success()` | Successful operations | "Property saved" |
| `error()` | Failures, errors | "Upload failed" |
| `warning()` | Cautions, alerts | "Unsaved changes" |
| `info()` | Informational | "New feature available" |

## 5. Options

```typescript
// With description
error('Upload failed', {
  description: 'File size exceeds 10MB'
});

// Custom duration (ms)
warning('Important', { duration: 10000 }); // 10 seconds

// No auto-dismiss
const id = info('Processing...', { duration: 0 });

// With action
success('Saved', {
  action: {
    label: 'View',
    onClick: () => navigate('/view')
  }
});
```

## 6. Manual Control

```typescript
const { info, dismiss } = useToast();

// Show toast
const id = info('Processing...', { duration: 0 });

// Dismiss later
setTimeout(() => {
  dismiss(id);
  success('Complete!');
}, 3000);
```

## 7. Testing

Visit the demo page to test all features:

```typescript
// Add to your router
{
  path: '/demo/toasts',
  element: <ToastDemo />
}
```

Then navigate to `/demo/toasts` in your app.

## 8. Full Documentation

For complete details, see:
- **docs/toast-notifications.md** - Complete API and patterns
- **docs/toast-visual-reference.md** - Visual specs and styling
- **TOAST_IMPLEMENTATION_SUMMARY.md** - Technical overview

## Quick Reference

```typescript
import { useToast } from '@/hooks/useToast';
import { AlertBanner } from '@/components/ui';

const { success, error, warning, info, toast, dismiss } = useToast();

// Basic
success('Success message');
error('Error message');
warning('Warning message');
info('Info message');

// With options
success('Title', {
  description: 'Additional details',
  duration: 5000,
  action: {
    label: 'Action',
    onClick: () => {}
  }
});

// Manual control
const id = info('Message', { duration: 0 });
dismiss(id);

// Alert banner
<AlertBanner
  variant="success"
  title="Title"
  description="Description"
  dismissible
  action={{ label: 'Action', onClick: () => {} }}
/>
```

## That's It!

You're ready to use toast notifications throughout your app. Import, call, done! 🎉
