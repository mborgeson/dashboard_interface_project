/**
 * ActivityForm - Form to add new activity to a deal
 */
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { useAddDealActivity } from '@/hooks/api/useDeals';
import type { DealActivity } from '@/hooks/api/useDeals';
import {
  ArrowRight,
  FileText,
  File,
  Phone,
  Mail,
  Calendar,
  MoreHorizontal,
  Loader2,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ActivityFormProps {
  dealId: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

const activitySchema = z.object({
  type: z.enum(['stage_change', 'note', 'document', 'call', 'email', 'meeting', 'other']),
  description: z.string().min(1, 'Description is required').max(500, 'Description is too long'),
});

type ActivityFormValues = z.infer<typeof activitySchema>;

type ActivityType = DealActivity['type'];

interface ActivityTypeOption {
  value: ActivityType;
  label: string;
  icon: LucideIcon;
}

const ACTIVITY_TYPES: ActivityTypeOption[] = [
  { value: 'note', label: 'Note', icon: FileText },
  { value: 'call', label: 'Call', icon: Phone },
  { value: 'email', label: 'Email', icon: Mail },
  { value: 'meeting', label: 'Meeting', icon: Calendar },
  { value: 'document', label: 'Document', icon: File },
  { value: 'stage_change', label: 'Stage Change', icon: ArrowRight },
  { value: 'other', label: 'Other', icon: MoreHorizontal },
];

export function ActivityForm({ dealId, onSuccess, onCancel }: ActivityFormProps) {
  const addActivityMutation = useAddDealActivity();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<ActivityFormValues>({
    resolver: zodResolver(activitySchema),
    defaultValues: {
      type: 'note',
      description: '',
    },
  });

  const selectedType = watch('type');

  const onSubmit = async (values: ActivityFormValues) => {
    try {
      await addActivityMutation.mutateAsync({
        dealId,
        type: values.type,
        description: values.description,
        user: 'Current User', // In real app, this would come from auth context
      });
      onSuccess?.();
    } catch (error) {
      console.error('Failed to add activity:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* Activity Type Selection */}
      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-2">
          Activity Type
        </label>
        <div className="flex flex-wrap gap-2">
          {ACTIVITY_TYPES.map((type) => {
            const Icon = type.icon;
            const isSelected = selectedType === type.value;
            return (
              <button
                key={type.value}
                type="button"
                onClick={() => setValue('type', type.value)}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  'border',
                  isSelected
                    ? 'bg-blue-50 border-blue-300 text-blue-700'
                    : 'bg-white border-neutral-200 text-neutral-600 hover:bg-neutral-50'
                )}
              >
                <Icon className="w-4 h-4" />
                {type.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Description */}
      <div>
        <label htmlFor="description" className="block text-sm font-medium text-neutral-700 mb-2">
          Description
        </label>
        <textarea
          id="description"
          {...register('description')}
          rows={3}
          placeholder="Enter activity details..."
          className={cn(
            'w-full px-3 py-2 rounded-lg border text-sm transition-colors',
            'focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder:text-neutral-400',
            errors.description
              ? 'border-red-300 bg-red-50'
              : 'border-neutral-200 bg-white'
          )}
        />
        {errors.description && (
          <p className="mt-1 text-sm text-red-600">{errors.description.message}</p>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-2">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button
          type="submit"
          disabled={isSubmitting || addActivityMutation.isPending}
        >
          {(isSubmitting || addActivityMutation.isPending) && (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          )}
          Add Activity
        </Button>
      </div>
    </form>
  );
}
