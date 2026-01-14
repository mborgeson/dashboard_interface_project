/**
 * ParameterConfigStep - Dynamic parameter form based on template
 */
import type { ReportTemplate, ReportTemplateParameter } from '@/hooks/api/useReporting';
import { cn } from '@/lib/utils';

interface ParameterConfigStepProps {
  template: ReportTemplate;
  values: Record<string, unknown>;
  onChange: (values: Record<string, unknown>) => void;
  errors?: Record<string, string>;
}

export function ParameterConfigStep({
  template,
  values,
  onChange,
  errors = {},
}: ParameterConfigStepProps) {
  const handleChange = (paramName: string, value: unknown) => {
    onChange({ ...values, [paramName]: value });
  };

  return (
    <div className="space-y-4">
      <div className="pb-3 border-b border-neutral-200">
        <h4 className="text-sm font-medium text-neutral-900">{template.name}</h4>
        <p className="text-xs text-neutral-500 mt-1">{template.description}</p>
      </div>

      <div className="space-y-4 max-h-[360px] overflow-y-auto pr-1">
        {template.parameters.map((param) => (
          <ParameterField
            key={param.name}
            parameter={param}
            value={values[param.name]}
            onChange={(value) => handleChange(param.name, value)}
            error={errors[param.name]}
          />
        ))}
      </div>

      {template.parameters.length === 0 && (
        <div className="text-center py-8 text-neutral-500">
          <p className="font-medium">No configuration needed</p>
          <p className="text-sm">This template has no configurable parameters</p>
        </div>
      )}
    </div>
  );
}

interface ParameterFieldProps {
  parameter: ReportTemplateParameter;
  value: unknown;
  onChange: (value: unknown) => void;
  error?: string;
}

function ParameterField({ parameter, value, onChange, error }: ParameterFieldProps) {
  const inputClasses = cn(
    'w-full px-3 py-2 border rounded-lg text-sm transition-colors',
    'focus:outline-none focus:ring-2 focus:ring-blue-500',
    error
      ? 'border-red-300 bg-red-50'
      : 'border-neutral-200 bg-white'
  );

  const renderInput = () => {
    switch (parameter.type) {
      case 'string':
        return (
          <input
            type="text"
            value={(value as string) || (parameter.defaultValue as string) || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={`Enter ${parameter.label.toLowerCase()}`}
            className={inputClasses}
          />
        );

      case 'number':
        return (
          <input
            type="number"
            value={(value as number) ?? parameter.defaultValue ?? ''}
            onChange={(e) => onChange(e.target.value ? Number(e.target.value) : undefined)}
            placeholder={`Enter ${parameter.label.toLowerCase()}`}
            className={inputClasses}
          />
        );

      case 'boolean':
        return (
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={(value as boolean) ?? parameter.defaultValue ?? false}
              onChange={(e) => onChange(e.target.checked)}
              className="w-4 h-4 text-blue-600 border-neutral-300 rounded focus:ring-blue-500"
            />
            <span className="text-sm text-neutral-700">Enable this option</span>
          </label>
        );

      case 'date':
        return (
          <input
            type="date"
            value={(value as string) || ''}
            onChange={(e) => onChange(e.target.value)}
            className={inputClasses}
          />
        );

      case 'select':
        return (
          <select
            value={(value as string) || (parameter.defaultValue as string) || ''}
            onChange={(e) => onChange(e.target.value)}
            className={inputClasses}
          >
            <option value="">Select {parameter.label.toLowerCase()}</option>
            {parameter.options?.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        );

      case 'multiselect': {
        const selectedValues = (value as string[]) || [];
        return (
          <div className="space-y-2">
            {parameter.options?.map((opt) => (
              <label key={opt} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedValues.includes(opt)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      onChange([...selectedValues, opt]);
                    } else {
                      onChange(selectedValues.filter((v) => v !== opt));
                    }
                  }}
                  className="w-4 h-4 text-blue-600 border-neutral-300 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-neutral-700">{opt}</span>
              </label>
            ))}
          </div>
        );
      }

      default:
        return (
          <input
            type="text"
            value={(value as string) || ''}
            onChange={(e) => onChange(e.target.value)}
            className={inputClasses}
          />
        );
    }
  };

  return (
    <div>
      <label className="block text-sm font-medium text-neutral-700 mb-1.5">
        {parameter.label}
        {parameter.required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {parameter.description && (
        <p className="text-xs text-neutral-500 mb-2">{parameter.description}</p>
      )}
      {renderInput()}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}
