/**
 * TemplateSelectionStep - Template picker with search and filter
 */
import { useState, useMemo } from 'react';
import { Search, FileText, Check } from 'lucide-react';
import type { ReportTemplate } from '@/hooks/api/useReporting';
import { cn } from '@/lib/utils';

interface TemplateSelectionStepProps {
  templates: ReportTemplate[];
  selectedTemplateId: string | null;
  onSelect: (template: ReportTemplate) => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  financial: 'Financial',
  market: 'Market Analysis',
  portfolio: 'Portfolio',
  deal: 'Deal Pipeline',
  custom: 'Custom',
};

export function TemplateSelectionStep({
  templates,
  selectedTemplateId,
  onSelect,
}: TemplateSelectionStepProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  // Get unique categories
  const categories = useMemo(() => {
    const cats = new Set(templates.map((t) => t.category));
    return Array.from(cats);
  }, [templates]);

  // Filter templates
  const filteredTemplates = useMemo(() => {
    return templates.filter((template) => {
      const matchesSearch =
        searchQuery === '' ||
        template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        template.description.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesCategory =
        selectedCategory === null || template.category === selectedCategory;

      return matchesSearch && matchesCategory;
    });
  }, [templates, searchQuery, selectedCategory]);

  return (
    <div className="space-y-4">
      {/* Search and Filter */}
      <div className="flex gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
          <input
            type="text"
            placeholder="Search templates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          value={selectedCategory || ''}
          onChange={(e) => setSelectedCategory(e.target.value || null)}
          className="px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Categories</option>
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {CATEGORY_LABELS[cat] || cat}
            </option>
          ))}
        </select>
      </div>

      {/* Template Grid */}
      <div className="grid grid-cols-2 gap-3 max-h-[360px] overflow-y-auto pr-1">
        {filteredTemplates.map((template) => {
          const isSelected = template.id === selectedTemplateId;
          return (
            <button
              key={template.id}
              type="button"
              onClick={() => onSelect(template)}
              className={cn(
                'text-left p-4 rounded-lg border-2 transition-all',
                isSelected
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-neutral-200 hover:border-neutral-300 bg-white'
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <FileText className={cn(
                      'w-4 h-4 flex-shrink-0',
                      isSelected ? 'text-blue-600' : 'text-neutral-400'
                    )} />
                    <span className={cn(
                      'text-sm font-medium truncate',
                      isSelected ? 'text-blue-900' : 'text-neutral-900'
                    )}>
                      {template.name}
                    </span>
                  </div>
                  <p className="text-xs text-neutral-500 line-clamp-2">
                    {template.description}
                  </p>
                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-xs px-2 py-0.5 bg-neutral-100 rounded-full text-neutral-600">
                      {CATEGORY_LABELS[template.category] || template.category}
                    </span>
                    <span className="text-xs text-neutral-400">
                      {template.parameters.length} params
                    </span>
                  </div>
                </div>
                {isSelected && (
                  <div className="w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {filteredTemplates.length === 0 && (
        <div className="text-center py-8 text-neutral-500">
          <FileText className="w-12 h-12 mx-auto mb-3 text-neutral-300" />
          <p className="font-medium">No templates found</p>
          <p className="text-sm">Try adjusting your search or filters</p>
        </div>
      )}
    </div>
  );
}
