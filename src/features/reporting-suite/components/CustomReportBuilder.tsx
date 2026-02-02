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
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useReportWidgets, type ReportWidget } from '@/hooks/api/useReporting';

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
  const widgetIdCounter = useRef(0);

  // Fetch report widgets from API (with mock fallback)
  const { data: widgetData } = useReportWidgets();
  const allWidgets = widgetData?.widgets ?? [];

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
    console.log('Saving report:', { name: reportName, widgets: placedWidgets });
    // In production, this would save to the backend
  };

  const handlePreviewReport = () => {
    console.log('Previewing report');
    // In production, this would open a preview modal
  };

  const handleGenerateReport = () => {
    console.log('Generating report');
    // In production, this would trigger report generation
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
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-md transition-colors"
            >
              <Save className="w-4 h-4" />
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
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-primary-600 text-white hover:bg-primary-700 rounded-md transition-colors"
            >
              <Download className="w-4 h-4" />
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
                            console.log('Configure widget:', placed.id);
                          }}
                          className="p-1 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 rounded"
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
              onClick={() => console.log('Open advanced settings')}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 border border-neutral-200 rounded-md text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
            >
              <Settings className="w-4 h-4" />
              Advanced Settings
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
