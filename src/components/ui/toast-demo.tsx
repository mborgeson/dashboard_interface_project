import { useToast } from '@/hooks/useToast';
import { Button } from './button';
import { AlertBanner } from './alert-banner';
import { useState } from 'react';

/**
 * Toast Notifications Demo Component
 * 
 * This component demonstrates all the features of the toast notification system.
 * Usage examples:
 * 
 * Basic toasts:
 * const { success, error, warning, info } = useToast();
 * success('Property saved successfully');
 * error('Failed to upload document');
 * 
 * Toast with description:
 * error('Upload failed', { description: 'File size exceeds 10MB limit' });
 * 
 * Toast with action button:
 * success('Deal created', { 
 *   action: { 
 *     label: 'View Deal', 
 *     onClick: () => navigate('/deals/123') 
 *   } 
 * });
 * 
 * Custom duration (0 = no auto-dismiss):
 * info('Processing...', { duration: 0 });
 * 
 * Manual dismiss:
 * const id = success('Task started');
 * setTimeout(() => dismiss(id), 3000);
 */
export function ToastDemo() {
  const { success, error, warning, info, toast, dismiss } = useToast();
  const [showBanner, setShowBanner] = useState(true);

  return (
    <div className="space-y-8 p-8">
      <div>
        <h2 className="text-2xl font-bold mb-4">Toast Notifications Demo</h2>
        <p className="text-muted-foreground mb-6">
          Click the buttons below to see different toast notification types.
        </p>

        <div className="flex flex-wrap gap-4">
          <Button
            onClick={() => success('Property saved successfully')}
            variant="default"
          >
            Success Toast
          </Button>

          <Button
            onClick={() =>
              error('Failed to upload document', {
                description: 'File size exceeds 10MB limit',
              })
            }
            variant="destructive"
          >
            Error Toast
          </Button>

          <Button
            onClick={() =>
              warning('Unsaved changes', {
                description: 'You have unsaved changes that will be lost',
              })
            }
            variant="outline"
          >
            Warning Toast
          </Button>

          <Button
            onClick={() =>
              info('New feature available', {
                description: 'Check out the new analytics dashboard',
              })
            }
            variant="secondary"
          >
            Info Toast
          </Button>

          <Button
            onClick={() => {
              const id = success('Deal created successfully', {
                action: {
                  label: 'View Deal',
                  onClick: () => {
                    console.log('Navigating to deal...');
                    alert('Navigate to deal details');
                  },
                },
                duration: 10000, // 10 seconds
              });
              console.log('Toast ID:', id);
            }}
            variant="default"
          >
            Toast with Action
          </Button>

          <Button
            onClick={() => {
              const id = info('Processing documents...', {
                duration: 0, // No auto-dismiss
              });
              
              // Simulate async operation
              setTimeout(() => {
                dismiss(id);
                success('Documents processed successfully');
              }, 3000);
            }}
            variant="secondary"
          >
            Persistent Toast
          </Button>

          <Button
            onClick={() => {
              // Show multiple toasts
              success('Property 1 saved');
              setTimeout(() => info('Property 2 updated'), 200);
              setTimeout(() => warning('Property 3 needs review'), 400);
              setTimeout(() => error('Property 4 failed validation'), 600);
            }}
            variant="outline"
          >
            Multiple Toasts
          </Button>

          <Button
            onClick={() => {
              toast({
                type: 'success',
                title: 'Custom Toast',
                description: 'This toast was created using the toast() function',
                duration: 7000,
                action: {
                  label: 'Learn More',
                  onClick: () => console.log('Learn more clicked'),
                },
              });
            }}
            variant="ghost"
          >
            Custom Toast
          </Button>
        </div>
      </div>

      <div>
        <h2 className="text-2xl font-bold mb-4">Alert Banners Demo</h2>
        <p className="text-muted-foreground mb-6">
          Full-width banners for page-level alerts and messages.
        </p>

        <div className="space-y-4">
          {showBanner && (
            <AlertBanner
              variant="info"
              title="New features available"
              description="We've added new analytics features to help you track property performance."
              dismissible
              onDismiss={() => setShowBanner(false)}
              action={{
                label: 'Learn More',
                onClick: () => console.log('Learn more clicked'),
              }}
            />
          )}

          <AlertBanner
            variant="success"
            title="Property successfully saved"
            description="All changes have been saved to your portfolio."
          />

          <AlertBanner
            variant="warning"
            title="Payment method expiring soon"
            description="Your credit card ending in 4242 expires next month."
            action={{
              label: 'Update Payment',
              onClick: () => console.log('Update payment clicked'),
            }}
          />

          <AlertBanner
            variant="error"
            title="Document upload failed"
            description="The file could not be uploaded. Please try again or contact support."
            dismissible
            action={{
              label: 'Retry',
              onClick: () => console.log('Retry clicked'),
            }}
          />
        </div>
      </div>

      <div className="bg-muted/50 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-2">Usage Examples</h3>
        <pre className="text-sm overflow-x-auto">
          <code>{`
// Import the hook
import { useToast } from '@/hooks/useToast';

function MyComponent() {
  const { success, error, warning, info, dismiss } = useToast();

  // Basic usage
  const handleSave = async () => {
    try {
      await saveProperty(data);
      success('Property saved successfully');
    } catch (err) {
      error('Failed to save property', {
        description: err.message
      });
    }
  };

  // With action button
  const handleCreate = async () => {
    const result = await createDeal(data);
    success('Deal created', {
      action: {
        label: 'View Deal',
        onClick: () => navigate(\`/deals/\${result.id}\`)
      }
    });
  };

  // Persistent toast with manual dismiss
  const handleProcess = async () => {
    const id = info('Processing...', { duration: 0 });
    await processDocuments();
    dismiss(id);
    success('Processing complete');
  };

  return <div>...</div>;
}
          `}</code>
        </pre>
      </div>
    </div>
  );
}
