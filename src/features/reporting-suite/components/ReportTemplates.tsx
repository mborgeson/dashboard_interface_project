import { useState } from 'react';
import {
  FileText,
  Download,
  Eye,
  Copy,
  Star,
  Search,
  Filter,
  LayoutGrid,
  List,
  Clock,
  User,
  FileSpreadsheet,
  Presentation,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useReportTemplates,
  type ReportTemplate,
} from '@/hooks/api/useReporting';

type ViewMode = 'grid' | 'list';
type CategoryFilter = 'all' | ReportTemplate['category'];

const categoryLabels: Record<ReportTemplate['category'], string> = {
  executive: 'Executive',
  financial: 'Financial',
  market: 'Market',
  portfolio: 'Portfolio',
  custom: 'Custom',
};

const categoryColors: Record<ReportTemplate['category'], string> = {
  executive: 'bg-purple-100 text-purple-700 border-purple-200',
  financial: 'bg-green-100 text-green-700 border-green-200',
  market: 'bg-blue-100 text-blue-700 border-blue-200',
  portfolio: 'bg-amber-100 text-amber-700 border-amber-200',
  custom: 'bg-neutral-100 text-neutral-700 border-neutral-200',
};

const formatIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  pdf: FileText,
  excel: FileSpreadsheet,
  pptx: Presentation,
};

export function ReportTemplates() {
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>('all');
  const [selectedTemplate, setSelectedTemplate] = useState<ReportTemplate | null>(null);

  // Fetch templates from API (with mock fallback)
  const { data: templateData } = useReportTemplates();
  const templates = templateData?.templates ?? [];

  const filteredTemplates = templates.filter(template => {
    const matchesSearch =
      template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = categoryFilter === 'all' || template.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  const handleGenerateReport = (template: ReportTemplate, format: string) => {
    console.log(`Generating ${format} report from template: ${template.name}`);
    // In production, this would trigger the report generation
  };

  return (
    <div className="space-y-6">
      {/* Header Controls */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1">
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
            <input
              type="text"
              placeholder="Search templates..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          {/* Category Filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
            <select
              value={categoryFilter}
              onChange={e => setCategoryFilter(e.target.value as CategoryFilter)}
              className="pl-10 pr-8 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 appearance-none bg-white"
            >
              <option value="all">All Categories</option>
              {Object.entries(categoryLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* View Toggle */}
        <div className="flex items-center gap-1 bg-neutral-100 rounded-lg p-1">
          <button
            onClick={() => setViewMode('grid')}
            className={cn(
              'p-2 rounded-md transition-colors',
              viewMode === 'grid' ? 'bg-white shadow-sm text-primary-600' : 'text-neutral-600 hover:text-neutral-900'
            )}
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={cn(
              'p-2 rounded-md transition-colors',
              viewMode === 'list' ? 'bg-white shadow-sm text-primary-600' : 'text-neutral-600 hover:text-neutral-900'
            )}
          >
            <List className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Templates Grid/List */}
      {viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTemplates.map(template => (
            <div
              key={template.id}
              className="bg-white rounded-lg border border-neutral-200 hover:border-primary-300 hover:shadow-md transition-all cursor-pointer"
              onClick={() => setSelectedTemplate(template)}
            >
              {/* Template Preview */}
              <div className="h-32 bg-gradient-to-br from-neutral-100 to-neutral-50 rounded-t-lg flex items-center justify-center border-b border-neutral-100">
                <FileText className="w-12 h-12 text-neutral-300" />
              </div>

              {/* Template Info */}
              <div className="p-4">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h3 className="font-semibold text-neutral-900">{template.name}</h3>
                  {template.isDefault && <Star className="w-4 h-4 text-amber-500 fill-amber-500 flex-shrink-0" />}
                </div>

                <span
                  className={cn(
                    'inline-block px-2 py-0.5 rounded-full text-xs font-medium border mb-2',
                    categoryColors[template.category]
                  )}
                >
                  {categoryLabels[template.category]}
                </span>

                <p className="text-sm text-neutral-600 line-clamp-2 mb-3">{template.description}</p>

                <div className="flex items-center justify-between text-xs text-neutral-500">
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    <span>{new Date(template.lastModified).toLocaleDateString()}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    {template.supportedFormats.map(format => {
                      const Icon = formatIcons[format];
                      return <Icon key={format} className="w-4 h-4" />;
                    })}
                  </div>
                </div>
              </div>

              {/* Quick Actions */}
              <div className="px-4 py-3 border-t border-neutral-100 flex items-center gap-2">
                <button
                  onClick={e => {
                    e.stopPropagation();
                    handleGenerateReport(template, template.supportedFormats[0]);
                  }}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700 transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  Generate
                </button>
                <button
                  onClick={e => {
                    e.stopPropagation();
                    setSelectedTemplate(template);
                  }}
                  className="p-1.5 text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 rounded-md transition-colors"
                >
                  <Eye className="w-4 h-4" />
                </button>
                <button
                  onClick={e => {
                    e.stopPropagation();
                    console.log('Duplicate template:', template.id);
                  }}
                  className="p-1.5 text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 rounded-md transition-colors"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-neutral-200">
          <table className="w-full">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50">
                <th className="text-left px-4 py-3 text-sm font-medium text-neutral-700">Template</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-neutral-700">Category</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-neutral-700">Sections</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-neutral-700">Formats</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-neutral-700">Modified</th>
                <th className="text-right px-4 py-3 text-sm font-medium text-neutral-700">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredTemplates.map(template => (
                <tr
                  key={template.id}
                  className="border-b border-neutral-100 hover:bg-neutral-50 cursor-pointer"
                  onClick={() => setSelectedTemplate(template)}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <FileText className="w-5 h-5 text-neutral-400" />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-neutral-900">{template.name}</span>
                          {template.isDefault && <Star className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />}
                        </div>
                        <span className="text-xs text-neutral-500">{template.createdBy}</span>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn('px-2 py-0.5 rounded-full text-xs font-medium border', categoryColors[template.category])}
                    >
                      {categoryLabels[template.category]}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-neutral-600">{template.sections.length} sections</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      {template.supportedFormats.map(format => {
                        const Icon = formatIcons[format];
                        return (
                          <span key={format} className="p-1 bg-neutral-100 rounded" title={format.toUpperCase()}>
                            <Icon className="w-3.5 h-3.5 text-neutral-600" />
                          </span>
                        );
                      })}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-neutral-600">{new Date(template.lastModified).toLocaleDateString()}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={e => {
                          e.stopPropagation();
                          handleGenerateReport(template, template.supportedFormats[0]);
                        }}
                        className="px-3 py-1.5 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700 transition-colors"
                      >
                        Generate
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Template Detail Modal */}
      {selectedTemplate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedTemplate(null)}>
          <div
            className="bg-white rounded-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}
          >
            <div className="p-6 border-b border-neutral-200">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h2 className="text-xl font-semibold text-neutral-900">{selectedTemplate.name}</h2>
                    {selectedTemplate.isDefault && <Star className="w-5 h-5 text-amber-500 fill-amber-500" />}
                  </div>
                  <span
                    className={cn('px-2 py-0.5 rounded-full text-xs font-medium border', categoryColors[selectedTemplate.category])}
                  >
                    {categoryLabels[selectedTemplate.category]}
                  </span>
                </div>
                <button onClick={() => setSelectedTemplate(null)} className="text-neutral-400 hover:text-neutral-600">
                  <span className="sr-only">Close</span>
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            <div className="p-6 space-y-6">
              <div>
                <h3 className="text-sm font-medium text-neutral-700 mb-2">Description</h3>
                <p className="text-neutral-600">{selectedTemplate.description}</p>
              </div>

              <div>
                <h3 className="text-sm font-medium text-neutral-700 mb-2">Sections</h3>
                <ul className="space-y-1">
                  {selectedTemplate.sections.map((section, index) => (
                    <li key={index} className="flex items-center gap-2 text-neutral-600">
                      <span className="w-5 h-5 rounded-full bg-primary-100 text-primary-700 text-xs flex items-center justify-center font-medium">
                        {index + 1}
                      </span>
                      {section}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="text-sm font-medium text-neutral-700 mb-2">Created By</h3>
                  <div className="flex items-center gap-2 text-neutral-600">
                    <User className="w-4 h-4" />
                    {selectedTemplate.createdBy}
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-neutral-700 mb-2">Last Modified</h3>
                  <div className="flex items-center gap-2 text-neutral-600">
                    <Clock className="w-4 h-4" />
                    {new Date(selectedTemplate.lastModified).toLocaleDateString()}
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-medium text-neutral-700 mb-3">Generate Report</h3>
                <div className="flex items-center gap-3">
                  {selectedTemplate.supportedFormats.map(format => {
                    const Icon = formatIcons[format];
                    return (
                      <button
                        key={format}
                        onClick={() => handleGenerateReport(selectedTemplate, format)}
                        className="flex items-center gap-2 px-4 py-2 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors"
                      >
                        <Icon className="w-5 h-5 text-neutral-600" />
                        <span className="font-medium text-neutral-700">{format.toUpperCase()}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {filteredTemplates.length === 0 && (
        <div className="bg-white rounded-lg border border-neutral-200 p-12 text-center">
          <FileText className="w-12 h-12 text-neutral-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-neutral-900 mb-1">No templates found</h3>
          <p className="text-neutral-500">Try adjusting your search or filter criteria</p>
        </div>
      )}
    </div>
  );
}
