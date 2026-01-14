/**
 * FormatSelectionStep - PDF/Excel/PPTX format selector
 */
import { FileText, Table2, Presentation, Check } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { ReportFormat, ReportTemplate } from '@/hooks/api/useReporting';
import { cn } from '@/lib/utils';

interface FormatSelectionStepProps {
  template: ReportTemplate;
  selectedFormat: ReportFormat | null;
  onSelect: (format: ReportFormat) => void;
}

interface FormatOption {
  value: ReportFormat;
  label: string;
  description: string;
  icon: LucideIcon;
  color: string;
}

const FORMAT_OPTIONS: FormatOption[] = [
  {
    value: 'pdf',
    label: 'PDF Document',
    description: 'Best for sharing and printing. Fixed layout with professional formatting.',
    icon: FileText,
    color: 'text-red-600 bg-red-50',
  },
  {
    value: 'excel',
    label: 'Excel Spreadsheet',
    description: 'Best for data analysis. Editable cells with formulas and charts.',
    icon: Table2,
    color: 'text-green-600 bg-green-50',
  },
  {
    value: 'pptx',
    label: 'PowerPoint Presentation',
    description: 'Best for presentations. Slide-based format with visuals.',
    icon: Presentation,
    color: 'text-orange-600 bg-orange-50',
  },
];

export function FormatSelectionStep({
  template,
  selectedFormat,
  onSelect,
}: FormatSelectionStepProps) {
  // Filter available formats based on template support
  const availableFormats = FORMAT_OPTIONS.filter((opt) =>
    template.supportedFormats.includes(opt.value)
  );

  return (
    <div className="space-y-4">
      <div className="pb-3 border-b border-neutral-200">
        <h4 className="text-sm font-medium text-neutral-900">Choose Output Format</h4>
        <p className="text-xs text-neutral-500 mt-1">
          Select how you want to receive your report
        </p>
      </div>

      <div className="space-y-3">
        {availableFormats.map((format) => {
          const Icon = format.icon;
          const isSelected = format.value === selectedFormat;

          return (
            <button
              key={format.value}
              type="button"
              onClick={() => onSelect(format.value)}
              className={cn(
                'w-full text-left p-4 rounded-lg border-2 transition-all',
                isSelected
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-neutral-200 hover:border-neutral-300 bg-white'
              )}
            >
              <div className="flex items-center gap-4">
                <div className={cn(
                  'w-12 h-12 rounded-lg flex items-center justify-center',
                  format.color
                )}>
                  <Icon className="w-6 h-6" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className={cn(
                      'text-sm font-medium',
                      isSelected ? 'text-blue-900' : 'text-neutral-900'
                    )}>
                      {format.label}
                    </span>
                    <span className="text-xs px-2 py-0.5 bg-neutral-100 rounded-full text-neutral-500 uppercase">
                      .{format.value}
                    </span>
                  </div>
                  <p className="text-xs text-neutral-500 mt-1">
                    {format.description}
                  </p>
                </div>
                {isSelected && (
                  <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
                    <Check className="w-4 h-4 text-white" />
                  </div>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {availableFormats.length === 0 && (
        <div className="text-center py-8 text-neutral-500">
          <FileText className="w-12 h-12 mx-auto mb-3 text-neutral-300" />
          <p className="font-medium">No formats available</p>
          <p className="text-sm">This template doesn't support any output formats</p>
        </div>
      )}
    </div>
  );
}
