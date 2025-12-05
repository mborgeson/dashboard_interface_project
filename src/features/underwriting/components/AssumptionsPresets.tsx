import { Button } from '@/components/ui/button';
import type { UnderwritingInputs, AssumptionPreset } from '@/types';
import { Save, Upload, Download } from 'lucide-react';

interface AssumptionsPresetsProps {
  onLoadPreset: (inputs: Partial<UnderwritingInputs>) => void;
  currentInputs: UnderwritingInputs;
}

const CONSERVATIVE_PRESET: AssumptionPreset = {
  name: 'Conservative',
  description: 'Conservative underwriting assumptions for value-add deals',
  inputs: {
    // Financing - lower leverage
    ltvPercent: 0.65,
    interestRate: 0.07,
    amortizationPeriod: 30,
    interestOnlyPeriod: 0,

    // Revenue - conservative growth
    rentGrowthPercent: 0.02,
    vacancyPercent: 0.08,
    concessionsPercent: 0.03,
    badDebtPercent: 0.02,

    // Expenses - higher reserves
    managementPercent: 0.05,
    expenseGrowthPercent: 0.04,
    capitalReservePerUnit: 350,

    // Exit - higher cap rate
    exitCapRate: 0.06,
    capRateSpread: 0.005, // 50 bps expansion
  },
};

const MODERATE_PRESET: AssumptionPreset = {
  name: 'Moderate',
  description: 'Balanced assumptions for stabilized assets',
  inputs: {
    // Financing - standard leverage
    ltvPercent: 0.70,
    interestRate: 0.065,
    amortizationPeriod: 30,
    interestOnlyPeriod: 2,

    // Revenue - market growth
    rentGrowthPercent: 0.03,
    vacancyPercent: 0.05,
    concessionsPercent: 0.02,
    badDebtPercent: 0.01,

    // Expenses - standard reserves
    managementPercent: 0.04,
    expenseGrowthPercent: 0.03,
    capitalReservePerUnit: 300,

    // Exit - stable cap rate
    exitCapRate: 0.055,
    capRateSpread: 0, // No change
  },
};

const AGGRESSIVE_PRESET: AssumptionPreset = {
  name: 'Aggressive',
  description: 'Optimistic assumptions for best-in-class properties',
  inputs: {
    // Financing - higher leverage
    ltvPercent: 0.75,
    interestRate: 0.06,
    amortizationPeriod: 30,
    interestOnlyPeriod: 3,

    // Revenue - strong growth
    rentGrowthPercent: 0.04,
    vacancyPercent: 0.03,
    concessionsPercent: 0.01,
    badDebtPercent: 0.005,

    // Expenses - lower reserves
    managementPercent: 0.035,
    expenseGrowthPercent: 0.025,
    capitalReservePerUnit: 250,

    // Exit - compression
    exitCapRate: 0.05,
    capRateSpread: -0.005, // 50 bps compression
  },
};

const PRESETS = [CONSERVATIVE_PRESET, MODERATE_PRESET, AGGRESSIVE_PRESET];

export function AssumptionsPresets({ onLoadPreset, currentInputs }: AssumptionsPresetsProps) {
  const handleSaveCustom = () => {
    const presetName = prompt('Enter a name for this preset:');
    if (!presetName) return;

    const customPresets = JSON.parse(localStorage.getItem('customPresets') || '[]');
    customPresets.push({
      name: presetName,
      description: 'Custom preset',
      inputs: currentInputs,
      timestamp: Date.now(),
    });

    localStorage.setItem('customPresets', JSON.stringify(customPresets));
    alert('Preset saved successfully!');
  };

  const handleLoadCustom = () => {
    const customPresets = JSON.parse(localStorage.getItem('customPresets') || '[]');
    
    if (customPresets.length === 0) {
      alert('No custom presets saved');
      return;
    }

    // Simple selection via prompt (could be enhanced with a modal)
    const presetNames = customPresets.map((p: any, i: number) => `${i + 1}. ${p.name}`).join('\n');
    const selection = prompt(`Select a preset:\n${presetNames}\n\nEnter number:`);
    
    if (!selection) return;
    
    const index = parseInt(selection) - 1;
    if (index >= 0 && index < customPresets.length) {
      onLoadPreset(customPresets[index].inputs);
    }
  };

  const handleExportPreset = () => {
    const preset = {
      name: currentInputs.propertyName || 'Exported Preset',
      inputs: currentInputs,
      exportedAt: new Date().toISOString(),
    };

    const blob = new Blob([JSON.stringify(preset, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `underwriting-preset-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImportPreset = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const preset = JSON.parse(event.target?.result as string);
          if (preset.inputs) {
            onLoadPreset(preset.inputs);
            alert('Preset imported successfully!');
          }
        } catch (error) {
          alert('Error importing preset. Please check the file format.');
        }
      };
      reader.readAsText(file);
    };

    input.click();
  };

  return (
    <div className="space-y-4">
      {/* Standard Presets */}
      <div>
        <h4 className="text-sm font-medium text-neutral-700 mb-2">Standard Presets</h4>
        <div className="grid grid-cols-3 gap-3">
          {PRESETS.map((preset) => (
            <button
              key={preset.name}
              onClick={() => onLoadPreset(preset.inputs)}
              className="p-4 text-left border border-neutral-200 rounded-lg hover:border-primary-400 hover:bg-primary-50 transition-colors group"
            >
              <div className="font-medium text-neutral-900 group-hover:text-primary-700">
                {preset.name}
              </div>
              <div className="text-xs text-neutral-500 mt-1">{preset.description}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Custom Presets Actions */}
      <div className="pt-4 border-t border-neutral-200">
        <h4 className="text-sm font-medium text-neutral-700 mb-2">Custom Presets</h4>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleSaveCustom}>
            <Save className="w-4 h-4 mr-1" />
            Save Current
          </Button>
          <Button variant="outline" size="sm" onClick={handleLoadCustom}>
            <Upload className="w-4 h-4 mr-1" />
            Load Custom
          </Button>
          <Button variant="outline" size="sm" onClick={handleExportPreset}>
            <Download className="w-4 h-4 mr-1" />
            Export
          </Button>
          <Button variant="outline" size="sm" onClick={handleImportPreset}>
            <Upload className="w-4 h-4 mr-1" />
            Import
          </Button>
        </div>
      </div>

      {/* Preset Indicators */}
      <div className="p-3 bg-neutral-50 rounded-lg text-xs text-neutral-600">
        <div className="font-medium mb-1">Current Settings:</div>
        <div className="grid grid-cols-3 gap-2">
          <div>LTV: {((currentInputs.ltvPercent || 0) * 100).toFixed(0)}%</div>
          <div>Vacancy: {((currentInputs.vacancyPercent || 0) * 100).toFixed(1)}%</div>
          <div>Exit Cap: {((currentInputs.exitCapRate || 0) * 100).toFixed(2)}%</div>
        </div>
      </div>
    </div>
  );
}
