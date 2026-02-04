import { useState } from 'react';
import {
  Save,
  Upload,
  Palette,
  FileText,
  Layout,
  Hash,
  Clock,
  Shield,
  Type,
  Image,
  RotateCcw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { defaultReportSettings, type ReportSettings as ReportSettingsType } from '@/data/mockReportingData';

const fontOptions = [
  { value: 'Inter', label: 'Inter (Default)' },
  { value: 'Roboto', label: 'Roboto' },
  { value: 'Open Sans', label: 'Open Sans' },
  { value: 'Lato', label: 'Lato' },
  { value: 'Source Sans Pro', label: 'Source Sans Pro' },
  { value: 'Georgia', label: 'Georgia (Serif)' },
  { value: 'Times New Roman', label: 'Times New Roman (Serif)' },
];

const pageSizeOptions = [
  { value: 'letter', label: 'Letter (8.5" × 11")' },
  { value: 'a4', label: 'A4 (210mm × 297mm)' },
  { value: 'legal', label: 'Legal (8.5" × 14")' },
];

const orientationOptions = [
  { value: 'portrait', label: 'Portrait' },
  { value: 'landscape', label: 'Landscape' },
];

export function ReportSettings() {
  const [settings, setSettings] = useState<ReportSettingsType>(defaultReportSettings);
  const [hasChanges, setHasChanges] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savedMessage, setSavedMessage] = useState('');

  const handleChange = <K extends keyof ReportSettingsType>(key: K, value: ReportSettingsType[K]) => {
    setSettings(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
    setSavedMessage('');
  };

  const handleSave = async () => {
    setSaving(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    setSaving(false);
    setHasChanges(false);
    setSavedMessage('Settings saved successfully!');
    setTimeout(() => setSavedMessage(''), 3000);
  };

  const handleReset = () => {
    setSettings(defaultReportSettings);
    setHasChanges(true);
    setSavedMessage('');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-neutral-900">Report Settings</h2>
          <p className="text-sm text-neutral-500">Configure default settings for all generated reports</p>
        </div>
        <div className="flex items-center gap-3">
          {savedMessage && (
            <span className="text-sm text-green-600 font-medium">{savedMessage}</span>
          )}
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Reset to Defaults
          </button>
          <button
            onClick={handleSave}
            disabled={!hasChanges || saving}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              hasChanges
                ? 'bg-primary-600 text-white hover:bg-primary-700'
                : 'bg-neutral-100 text-neutral-400 cursor-not-allowed'
            )}
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Branding Section */}
        <div className="bg-white rounded-lg border border-neutral-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Palette className="w-5 h-5 text-primary-600" />
            <h3 className="font-semibold text-neutral-900">Branding</h3>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Company Name</label>
              <input
                type="text"
                value={settings.companyName}
                onChange={e => handleChange('companyName', e.target.value)}
                className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Company Logo</label>
              <div className="flex items-center gap-3">
                <div className="w-16 h-16 bg-neutral-100 rounded-lg flex items-center justify-center border border-neutral-200">
                  {settings.companyLogo ? (
                    <img src={settings.companyLogo} alt="Logo" className="max-w-full max-h-full" />
                  ) : (
                    <Image className="w-6 h-6 text-neutral-400" />
                  )}
                </div>
                <label className="flex items-center gap-2 px-3 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors cursor-pointer">
                  <Upload className="w-4 h-4" />
                  Upload Logo
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={e => {
                      const file = e.target.files?.[0];
                      if (file) {
                        const reader = new FileReader();
                        reader.onload = ev => {
                          handleChange('companyLogo', ev.target?.result as string);
                        };
                        reader.readAsDataURL(file);
                      }
                    }}
                  />
                </label>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">Primary Color</label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={settings.primaryColor}
                    onChange={e => handleChange('primaryColor', e.target.value)}
                    className="w-10 h-10 rounded border border-neutral-200 cursor-pointer"
                  />
                  <input
                    type="text"
                    value={settings.primaryColor}
                    onChange={e => handleChange('primaryColor', e.target.value)}
                    className="flex-1 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">Secondary Color</label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={settings.secondaryColor}
                    onChange={e => handleChange('secondaryColor', e.target.value)}
                    className="w-10 h-10 rounded border border-neutral-200 cursor-pointer"
                  />
                  <input
                    type="text"
                    value={settings.secondaryColor}
                    onChange={e => handleChange('secondaryColor', e.target.value)}
                    className="flex-1 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Page Layout Section */}
        <div className="bg-white rounded-lg border border-neutral-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Layout className="w-5 h-5 text-primary-600" />
            <h3 className="font-semibold text-neutral-900">Page Layout</h3>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Default Font</label>
              <select
                value={settings.defaultFont}
                onChange={e => handleChange('defaultFont', e.target.value)}
                className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {fontOptions.map(font => (
                  <option key={font.value} value={font.value}>
                    {font.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">Page Size</label>
                <select
                  value={settings.defaultPageSize}
                  onChange={e => handleChange('defaultPageSize', e.target.value as 'letter' | 'a4' | 'legal')}
                  className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  {pageSizeOptions.map(size => (
                    <option key={size.value} value={size.value}>
                      {size.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">Orientation</label>
                <select
                  value={settings.defaultOrientation}
                  onChange={e => handleChange('defaultOrientation', e.target.value as 'portrait' | 'landscape')}
                  className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  {orientationOptions.map(orientation => (
                    <option key={orientation.value} value={orientation.value}>
                      {orientation.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Content Options Section */}
        <div className="bg-white rounded-lg border border-neutral-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <FileText className="w-5 h-5 text-primary-600" />
            <h3 className="font-semibold text-neutral-900">Content Options</h3>
          </div>

          <div className="space-y-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.includePageNumbers}
                onChange={e => handleChange('includePageNumbers', e.target.checked)}
                className="w-4 h-4 rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
              />
              <div className="flex items-center gap-2">
                <Hash className="w-4 h-4 text-neutral-500" />
                <span className="text-sm text-neutral-700">Include page numbers</span>
              </div>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.includeTableOfContents}
                onChange={e => handleChange('includeTableOfContents', e.target.checked)}
                className="w-4 h-4 rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
              />
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-neutral-500" />
                <span className="text-sm text-neutral-700">Include table of contents</span>
              </div>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.includeTimestamp}
                onChange={e => handleChange('includeTimestamp', e.target.checked)}
                className="w-4 h-4 rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
              />
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-neutral-500" />
                <span className="text-sm text-neutral-700">Include generation timestamp</span>
              </div>
            </label>
          </div>
        </div>

        {/* Header & Footer Section */}
        <div className="bg-white rounded-lg border border-neutral-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Type className="w-5 h-5 text-primary-600" />
            <h3 className="font-semibold text-neutral-900">Header & Footer</h3>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Header Text</label>
              <input
                type="text"
                value={settings.headerText}
                onChange={e => handleChange('headerText', e.target.value)}
                placeholder="Text to appear in report headers"
                className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Footer Text</label>
              <input
                type="text"
                value={settings.footerText}
                onChange={e => handleChange('footerText', e.target.value)}
                placeholder="Text to appear in report footers"
                className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Watermark Text
                <span className="text-neutral-400 font-normal"> (optional)</span>
              </label>
              <input
                type="text"
                value={settings.watermarkText || ''}
                onChange={e => handleChange('watermarkText', e.target.value || undefined)}
                placeholder="e.g., CONFIDENTIAL, DRAFT"
                className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Preview Section */}
      <div className="bg-white rounded-lg border border-neutral-200 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-5 h-5 text-primary-600" />
          <h3 className="font-semibold text-neutral-900">Preview</h3>
        </div>

        <div
          className="border border-neutral-200 rounded-lg p-8 bg-white"
          style={{
            fontFamily: settings.defaultFont,
          }}
        >
          {/* Header Preview */}
          <div
            className="pb-4 mb-4 border-b-2"
            style={{ borderColor: settings.primaryColor }}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded flex items-center justify-center text-white font-bold"
                  style={{ backgroundColor: settings.primaryColor }}
                >
                  {settings.companyName.charAt(0)}
                </div>
                <div>
                  <h4 className="font-semibold text-neutral-900">{settings.companyName}</h4>
                  <p className="text-xs text-neutral-500">{settings.headerText}</p>
                </div>
              </div>
              {settings.includeTimestamp && (
                <span className="text-xs text-neutral-500">
                  Generated: {new Date().toLocaleDateString()}
                </span>
              )}
            </div>
          </div>

          {/* Content Preview */}
          <div className="space-y-4 min-h-[200px]">
            {settings.includeTableOfContents && (
              <div className="bg-neutral-50 p-4 rounded">
                <h5 className="font-medium text-neutral-700 mb-2">Table of Contents</h5>
                <ul className="text-sm text-neutral-600 space-y-1">
                  <li>1. Executive Summary</li>
                  <li>2. Portfolio Overview</li>
                  <li>3. Financial Analysis</li>
                </ul>
              </div>
            )}

            <div>
              <h5 className="font-semibold text-lg mb-2" style={{ color: settings.primaryColor }}>
                Sample Section Header
              </h5>
              <p className="text-neutral-600 text-sm">
                This is a preview of how your report content will appear with the selected font and color settings.
                The layout reflects your page orientation and branding choices.
              </p>
            </div>

            {settings.watermarkText && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <span className="text-6xl font-bold text-neutral-100 transform rotate-[-30deg]">
                  {settings.watermarkText}
                </span>
              </div>
            )}
          </div>

          {/* Footer Preview */}
          <div className="pt-4 mt-4 border-t border-neutral-200 flex items-center justify-between text-xs text-neutral-500">
            <span>{settings.footerText}</span>
            {settings.includePageNumbers && <span>Page 1 of 10</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
