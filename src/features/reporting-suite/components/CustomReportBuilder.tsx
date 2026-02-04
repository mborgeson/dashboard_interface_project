import { useState, useRef } from 'react';
import {
  GripVertical,
  Plus,
  Trash2,
  Settings,
  Save,
  Eye,
  Download,
  LineChart,
  BarChart3,
  PieChart,
  Table,
  FileText,
  Image,
  Map,
  TrendingUp,
  LayoutGrid,
  Heading,
  Gauge,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useReportWidgets, useCreateReportTemplate, useGenerateReport, type ReportWidget } from '@/hooks/api/useReporting';
import { useToast } from '@/hooks/useToast';

interface PlacedWidget {
  id: string;
  widgetId: string;
  widget: ReportWidget;
  x: number;
  y: number;
  width: number;
  height: number;
}

const widgetIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  LineChart: LineChart,
  BarChart: BarChart3,
  PieChart: PieChart,
  AreaChart: LineChart,
  Table: Table,
  TableProperties: Table,
  TrendingUp: TrendingUp,
  LayoutGrid: LayoutGrid,
  Gauge: Gauge,
  FileText: FileText,
  Heading: Heading,
  Image: Image,
  Map: Map,
  MapPin: Map,
};

export function CustomReportBuilder() {
  const [reportName, setReportName] = useState('Untitled Report');
  const [placedWidgets, setPlacedWidgets] = useState<PlacedWidget[]>([]);
  const [selectedWidget, setSelectedWidget] = useState<PlacedWidget | null>(null);
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const [showPreview, setShowPreview] = useState(false);
  const widgetIdCounter = useRef(0);
  const { success, error: showError } = useToast();

  // Fetch report widgets from API (with mock fallback)
  const { data: widgetData } = useReportWidgets();
  const allWidgets = widgetData?.widgets ?? [];
  const saveTemplate = useCreateReportTemplate();
  const generateReport = useGenerateReport();

  const categories = ['all', ...Array.from(new Set(allWidgets.map(w => w.category)))];

  const filteredWidgets =
    activeCategory === 'all' ? allWidgets : allWidgets.filter(w => w.category === activeCategory);

  const handleAddWidget = (widget: ReportWidget) => {
    widgetIdCounter.current += 1;
    const newWidget: PlacedWidget = {
      id: `placed-${widgetIdCounter.current}`,
      widgetId: widget.id,
      widget,
      x: 0,
      y: placedWidgets.length * 2,
      width: widget.defaultWidth,
      height: widget.defaultHeight,
    };
    setPlacedWidgets([...placedWidgets, newWidget]);
  };

  const handleRemoveWidget = (id: string) => {
    setPlacedWidgets(placedWidgets.filter(w => w.id !== id));
    if (selectedWidget?.id === id) {
      setSelectedWidget(null);
    }
  };

  const handleSaveReport = () => {
    if (!reportName.trim() || reportName === 'Untitled Report') {
      showError('Please name your report');
      return;
    }
    saveTemplate.mutate(
      {
        name: reportName,
        description: `Custom report with ${placedWidgets.length} widgets`,
        category: 'custom',
        sections: placedWidgets.map(w => w.widget.name),
        export_formats: ['pdf'],
        config: {
          widgets: placedWidgets.map(w => ({
            widgetId: w.widgetId,
            width: w.width,
            height: w.height,
            x: w.x,
            y: w.y,
          })),
        },
      },
      {
        onSuccess: () => success('Report saved'),
        onError: () => showError('Save failed'),
      }
    );
  };

  const handlePreviewReport = () => {
    setShowPreview(true);
  };

  const handleGenerateReport = () => {
    if (placedWidgets.length === 0) {
      showError('Add at least one widget before generating');
      return;
    }
    // Save as template first, then generate
    saveTemplate.mutate(
      {
        name: reportName,
        description: `Custom report with ${placedWidgets.length} widgets`,
        category: 'custom',
        sections: placedWidgets.map(w => w.widget.name),
        export_formats: ['pdf'],
        config: {
          widgets: placedWidgets.map(w => ({
            widgetId: w.widgetId,
            width: w.width,
            height: w.height,
          })),
        },
      },
      {
        onSuccess: (data) => {
          generateReport.mutate(
            {
              template_id: data.id,
              name: `${reportName} - ${new Date().toLocaleDateString()}`,
              format: 'pdf',
            },
            {
              onSuccess: () => success('Report queued', { description: 'Check the Queue tab for progress' }),
              onError: () => showError('Generation failed'),
            }
          );
        },
        onError: () => showError('Could not save report template'),
      }
    );
  };

  return (
    <div className="flex gap-6 h-[calc(100vh-240px)]">
      {/* Widget Library */}
      <div className="w-72 flex-shrink-0 bg-white rounded-lg border border-neutral-200 flex flex-col">
        <div className="p-4 border-b border-neutral-200">
          <h3 className="font-semibold text-neutral-900 mb-3">Widget Library</h3>
          <div className="flex flex-wrap gap-1">
            {categories.map(category => (
              <button
                key={category}
                onClick={() => setActiveCategory(category)}
                className={cn(
                  'px-2 py-1 rounded text-xs font-medium transition-colors capitalize',
                  activeCategory === category
                    ? 'bg-primary-100 text-primary-700'
                    : 'text-neutral-600 hover:bg-neutral-100'
                )}
              >
                {category}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {filteredWidgets.map(widget => {
            const Icon = widgetIcons[widget.icon] || FileText;
            return (
              <div
                key={widget.id}
                draggable
                onDragEnd={() => handleAddWidget(widget)}
                className="flex items-center gap-3 p-3 bg-neutral-50 rounded-lg border border-neutral-200 cursor-grab hover:border-primary-300 hover:bg-primary-50 transition-colors group"
              >
                <div className="p-2 bg-white rounded-md border border-neutral-200 group-hover:border-primary-200">
                  <Icon className="w-5 h-5 text-neutral-600 group-hover:text-primary-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-neutral-900 truncate">{widget.name}</p>
                  <p className="text-xs text-neutral-500 truncate">{widget.description}</p>
                </div>
                <button
                  onClick={() => handleAddWidget(widget)}
                  className="p-1 text-neutral-400 hover:text-primary-600 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Canvas Area */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="bg-white rounded-t-lg border border-neutral-200 border-b-0 p-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <input
              type="text"
              value={reportName}
              onChange={e => setReportName(e.target.value)}
              className="text-lg font-semibold text-neutral-900 bg-transparent border-none focus:outline-none focus:ring-0 p-0"
            />
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleSaveReport}
              disabled={saveTemplate.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-md transition-colors disabled:opacity-50"
            >
              {saveTemplate.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Save
            </button>
            <button
              onClick={handlePreviewReport}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-md transition-colors"
            >
              <Eye className="w-4 h-4" />
              Preview
            </button>
            <button
              onClick={handleGenerateReport}
              disabled={generateReport.isPending || saveTemplate.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-primary-600 text-white hover:bg-primary-700 rounded-md transition-colors disabled:opacity-50"
            >
              {generateReport.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              Generate
            </button>
          </div>
        </div>

        {/* Canvas */}
        <div className="flex-1 bg-white border border-neutral-200 rounded-b-lg overflow-y-auto">
          {placedWidgets.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8">
              <div className="w-16 h-16 rounded-full bg-neutral-100 flex items-center justify-center mb-4">
                <LayoutGrid className="w-8 h-8 text-neutral-400" />
              </div>
              <h3 className="text-lg font-medium text-neutral-900 mb-1">Start Building Your Report</h3>
              <p className="text-neutral-500 max-w-md mb-4">
                Drag widgets from the library or click the + button to add them to your report canvas.
              </p>
              <button
                onClick={() => setActiveCategory('all')}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add Widget
              </button>
            </div>
          ) : (
            <div className="p-6 space-y-4">
              {placedWidgets.map((placed) => {
                const Icon = widgetIcons[placed.widget.icon] || FileText;
                const isSelected = selectedWidget?.id === placed.id;
                return (
                  <div
                    key={placed.id}
                    onClick={() => setSelectedWidget(placed)}
                    className={cn(
                      'relative p-4 border-2 rounded-lg transition-all cursor-pointer',
                      isSelected ? 'border-primary-500 bg-primary-50' : 'border-neutral-200 hover:border-neutral-300 bg-white'
                    )}
                    style={{
                      gridColumn: `span ${placed.width}`,
                      minHeight: `${placed.height * 60}px`,
                    }}
                  >
                    {/* Widget Header */}
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <GripVertical className="w-4 h-4 text-neutral-400 cursor-grab" />
                        <Icon className="w-5 h-5 text-neutral-600" />
                        <span className="font-medium text-neutral-900">{placed.widget.name}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={e => {
                            e.stopPropagation();
                            setSelectedWidget(placed);
                          }}
                          className="p-1 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 rounded"
                          title="Configure widget"
                        >
                          <Settings className="w-4 h-4" />
                        </button>
                        <button
                          onClick={e => {
                            e.stopPropagation();
                            handleRemoveWidget(placed.id);
                          }}
                          className="p-1 text-neutral-400 hover:text-red-600 hover:bg-red-50 rounded"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* Widget Placeholder */}
                    <div className="bg-neutral-100 rounded-md flex items-center justify-center py-8 border border-dashed border-neutral-300">
                      <div className="text-center">
                        <Icon className="w-8 h-8 text-neutral-400 mx-auto mb-2" />
                        <p className="text-sm text-neutral-500">{placed.widget.description}</p>
                        <p className="text-xs text-neutral-400 mt-1">
                          Size: {placed.width} x {placed.height} units
                        </p>
                      </div>
                    </div>

                    {/* Selection indicator */}
                    {isSelected && (
                      <div className="absolute -top-2 -left-2 w-4 h-4 bg-primary-500 rounded-full border-2 border-white" />
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Preview Modal */}
      {showPreview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowPreview(false)}>
          <div className="bg-white rounded-xl max-w-4xl w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-neutral-200 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-neutral-900">Preview: {reportName}</h2>
              <button onClick={() => setShowPreview(false)} className="text-neutral-400 hover:text-neutral-600">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6 space-y-4">
              {placedWidgets.length === 0 ? (
                <p className="text-neutral-500 text-center py-8">No widgets added yet</p>
              ) : (
                placedWidgets.map(placed => {
                  const Icon = widgetIcons[placed.widget.icon] || FileText;
                  return (
                    <div key={placed.id} className="border border-neutral-200 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Icon className="w-5 h-5 text-neutral-600" />
                        <span className="font-medium text-neutral-900">{placed.widget.name}</span>
                        <span className="text-xs text-neutral-400">({placed.width} x {placed.height})</span>
                      </div>
                      <div className="bg-neutral-100 rounded-md py-8 flex items-center justify-center border border-dashed border-neutral-300">
                        <p className="text-sm text-neutral-500">{placed.widget.description}</p>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}

      {/* Properties Panel */}
      {selectedWidget && (
        <div className="w-64 flex-shrink-0 bg-white rounded-lg border border-neutral-200 p-4">
          <h3 className="font-semibold text-neutral-900 mb-4">Widget Properties</h3>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Widget Type</label>
              <p className="text-sm text-neutral-600">{selectedWidget.widget.name}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Width (columns)</label>
              <input
                type="range"
                min="1"
                max="12"
                value={selectedWidget.width}
                onChange={e => {
                  const newWidth = parseInt(e.target.value);
                  setPlacedWidgets(
                    placedWidgets.map(w => (w.id === selectedWidget.id ? { ...w, width: newWidth } : w))
                  );
                  setSelectedWidget({ ...selectedWidget, width: newWidth });
                }}
                className="w-full"
              />
              <p className="text-xs text-neutral-500 mt-1">{selectedWidget.width} of 12 columns</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Height (rows)</label>
              <input
                type="range"
                min="1"
                max="8"
                value={selectedWidget.height}
                onChange={e => {
                  const newHeight = parseInt(e.target.value);
                  setPlacedWidgets(
                    placedWidgets.map(w => (w.id === selectedWidget.id ? { ...w, height: newHeight } : w))
                  );
                  setSelectedWidget({ ...selectedWidget, height: newHeight });
                }}
                className="w-full"
              />
              <p className="text-xs text-neutral-500 mt-1">{selectedWidget.height} rows</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Data Source</label>
              <select className="w-full px-3 py-2 border border-neutral-200 rounded-md text-sm">
                <option>Portfolio Data</option>
                <option>Property Data</option>
                <option>Financial Data</option>
                <option>Market Data</option>
              </select>
            </div>

            <button
              onClick={() => success('Widget configured', { description: `${selectedWidget.widget.name} settings applied` })}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700 transition-colors"
            >
              <Settings className="w-4 h-4" />
              Apply Settings
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
