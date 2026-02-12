import { useState } from 'react';
import type { UnderwritingInputs, PropertyClass, AssetType, LoanType, PrepaymentPenaltyType } from '@/types';
import { Label } from '@/components/ui/label';
import { ChevronDown, ChevronRight, HelpCircle } from 'lucide-react';
import { AssumptionsPresets } from './AssumptionsPresets';

interface InputsTabProps {
  inputs: UnderwritingInputs;
  updateInput: <K extends keyof UnderwritingInputs>(key: K, value: UnderwritingInputs[K]) => void;
}

function InputField({
  label,
  name,
  value,
  onChange,
  type = 'number',
  prefix,
  suffix,
  step,
  tooltip,
  min,
  max,
}: {
  label: string;
  name: string;
  value: number | string;
  onChange: (value: number | string) => void;
  type?: 'number' | 'text';
  prefix?: string;
  suffix?: string;
  step?: string;
  tooltip?: string;
  min?: number;
  max?: number;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1">
        <Label htmlFor={name} className="text-sm text-neutral-600">
          {label}
        </Label>
        {tooltip && (
          <div className="group relative">
            <HelpCircle className="w-3 h-3 text-neutral-400" />
            <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block w-48 p-2 bg-neutral-800 text-white text-xs rounded shadow-lg z-10">
              {tooltip}
            </div>
          </div>
        )}
      </div>
      <div className="relative">
        {prefix && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500 text-sm">
            {prefix}
          </span>
        )}
        <input
          id={name}
          type={type}
          value={value}
          onChange={(e) =>
            onChange(type === 'number' ? parseFloat(e.target.value) || 0 : e.target.value)
          }
          step={step}
          min={min}
          max={max}
          className={`w-full rounded-md border border-neutral-300 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 ${
            prefix ? 'pl-7' : 'pl-3'
          } ${suffix ? 'pr-12' : 'pr-3'}`}
        />
        {suffix && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 text-sm">
            {suffix}
          </span>
        )}
      </div>
    </div>
  );
}

function SelectField({
  label,
  name,
  value,
  onChange,
  options,
  tooltip,
}: {
  label: string;
  name: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  tooltip?: string;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1">
        <Label htmlFor={name} className="text-sm text-neutral-600">
          {label}
        </Label>
        {tooltip && (
          <div className="group relative">
            <HelpCircle className="w-3 h-3 text-neutral-400" />
            <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block w-48 p-2 bg-neutral-800 text-white text-xs rounded shadow-lg z-10">
              {tooltip}
            </div>
          </div>
        )}
      </div>
      <select
        id={name}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-neutral-300 py-2 px-3 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function SliderField({
  label,
  name,
  value,
  onChange,
  min,
  max,
  step,
  suffix = '%',
  tooltip,
}: {
  label: string;
  name: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step: number;
  suffix?: string;
  tooltip?: string;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <Label htmlFor={name} className="text-sm text-neutral-600">
            {label}
          </Label>
          {tooltip && (
            <div className="group relative">
              <HelpCircle className="w-3 h-3 text-neutral-400" />
              <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block w-48 p-2 bg-neutral-800 text-white text-xs rounded shadow-lg z-10">
                {tooltip}
              </div>
            </div>
          )}
        </div>
        <span className="text-sm font-medium text-neutral-900">
          {(value * (suffix === '%' ? 100 : 1)).toFixed(suffix === '%' ? 1 : 0)}
          {suffix}
        </span>
      </div>
      <input
        id={name}
        type="range"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        min={min}
        max={max}
        step={step}
        className="w-full h-2 bg-neutral-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
      />
      <div className="flex justify-between text-xs text-neutral-400">
        <span>
          {(min * (suffix === '%' ? 100 : 1)).toFixed(0)}
          {suffix}
        </span>
        <span>
          {(max * (suffix === '%' ? 100 : 1)).toFixed(0)}
          {suffix}
        </span>
      </div>
    </div>
  );
}

function CollapsibleSection({
  title,
  children,
  defaultOpen = true,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-neutral-200 rounded-lg">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3 bg-neutral-50 hover:bg-neutral-100 transition-colors rounded-t-lg"
      >
        <h4 className="text-sm font-semibold text-neutral-800">{title}</h4>
        {isOpen ? (
          <ChevronDown className="w-4 h-4 text-neutral-600" />
        ) : (
          <ChevronRight className="w-4 h-4 text-neutral-600" />
        )}
      </button>
      {isOpen && <div className="p-4 space-y-4">{children}</div>}
    </div>
  );
}

export function InputsTab({ inputs, updateInput }: InputsTabProps) {
  const handleLoadPreset = (presetInputs: Partial<UnderwritingInputs>) => {
    Object.entries(presetInputs).forEach(([key, value]) => {
      if (value !== undefined) {
        updateInput(key as keyof UnderwritingInputs, value as UnderwritingInputs[keyof UnderwritingInputs]);
      }
    });
  };

  // Calculate derived values
  const pricePerUnit = inputs.purchasePrice / (inputs.units || 1);
  const pricePerSF = inputs.purchasePrice / (inputs.squareFeet || 1);
  const loanAmount = inputs.purchasePrice * (inputs.ltvPercent || 0);

  return (
    <div className="space-y-4">
      {/* Assumptions Presets */}
      <AssumptionsPresets onLoadPreset={handleLoadPreset} currentInputs={inputs} />

      <div className="grid grid-cols-2 gap-4">
        {/* Left Column */}
        <div className="space-y-4">
          {/* Property Assumptions */}
          <CollapsibleSection title="Property Assumptions">
            <div className="grid grid-cols-2 gap-4">
              <InputField
                label="Property Name"
                name="propertyName"
                type="text"
                value={inputs.propertyName}
                onChange={(v) => updateInput('propertyName', v as string)}
              />
              <InputField
                label="Address"
                name="address"
                type="text"
                value={inputs.address}
                onChange={(v) => updateInput('address', v as string)}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SelectField
                label="Property Class"
                name="propertyClass"
                value={inputs.propertyClass}
                onChange={(v) => updateInput('propertyClass', v as PropertyClass)}
                options={[
                  { value: 'A', label: 'Class A' },
                  { value: 'B', label: 'Class B' },
                  { value: 'C', label: 'Class C' },
                ]}
                tooltip="Property quality classification based on age, amenities, and location"
              />
              <SelectField
                label="Asset Type"
                name="assetType"
                value={inputs.assetType}
                onChange={(v) => updateInput('assetType', v as AssetType)}
                options={[
                  { value: 'Garden', label: 'Garden' },
                  { value: 'Mid-Rise', label: 'Mid-Rise' },
                  { value: 'High-Rise', label: 'High-Rise' },
                ]}
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <InputField
                label="Year Built"
                name="yearBuilt"
                value={inputs.yearBuilt}
                onChange={(v) => updateInput('yearBuilt', v as number)}
              />
              <InputField
                label="Units"
                name="units"
                value={inputs.units}
                onChange={(v) => updateInput('units', v as number)}
              />
              <InputField
                label="Avg Unit Size"
                name="averageUnitSize"
                value={inputs.averageUnitSize}
                onChange={(v) => updateInput('averageUnitSize', v as number)}
                suffix="SF"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <InputField
                label="Market"
                name="market"
                type="text"
                value={inputs.market}
                onChange={(v) => updateInput('market', v as string)}
              />
              <InputField
                label="Submarket"
                name="submarket"
                type="text"
                value={inputs.submarket}
                onChange={(v) => updateInput('submarket', v as string)}
              />
            </div>
          </CollapsibleSection>

          {/* Acquisition Assumptions */}
          <CollapsibleSection title="Acquisition Assumptions">
            <InputField
              label="Purchase Price"
              name="purchasePrice"
              value={inputs.purchasePrice}
              onChange={(v) => updateInput('purchasePrice', v as number)}
              prefix="$"
            />

            <div className="grid grid-cols-2 gap-4 p-3 bg-neutral-50 rounded">
              <div>
                <div className="text-xs text-neutral-500">Price/Unit</div>
                <div className="text-sm font-semibold text-neutral-900">
                  ${pricePerUnit.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </div>
              </div>
              <div>
                <div className="text-xs text-neutral-500">Price/SF</div>
                <div className="text-sm font-semibold text-neutral-900">
                  ${pricePerSF.toFixed(2)}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SliderField
                label="Closing Costs"
                name="closingCostsPercent"
                value={inputs.closingCostsPercent}
                onChange={(v) => updateInput('closingCostsPercent', v)}
                min={0.01}
                max={0.05}
                step={0.0025}
                tooltip="Title, escrow, recording fees, and other transaction costs"
              />
              <SliderField
                label="Acquisition Fee"
                name="acquisitionFeePercent"
                value={inputs.acquisitionFeePercent}
                onChange={(v) => updateInput('acquisitionFeePercent', v)}
                min={0}
                max={0.03}
                step={0.0025}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <InputField
                label="Due Diligence"
                name="dueDiligenceCosts"
                value={inputs.dueDiligenceCosts}
                onChange={(v) => updateInput('dueDiligenceCosts', v as number)}
                prefix="$"
                tooltip="Inspection, environmental, legal fees"
              />
              <InputField
                label="Immediate CapEx"
                name="immediateCapEx"
                value={inputs.immediateCapEx}
                onChange={(v) => updateInput('immediateCapEx', v as number)}
                prefix="$"
                tooltip="Day-one capital improvements"
              />
            </div>
          </CollapsibleSection>

          {/* Revenue Assumptions */}
          <CollapsibleSection title="Revenue Assumptions">
            <div className="grid grid-cols-2 gap-4">
              <InputField
                label="In-Place Rent"
                name="currentRentPerUnit"
                value={inputs.currentRentPerUnit}
                onChange={(v) => updateInput('currentRentPerUnit', v as number)}
                prefix="$"
                suffix="/mo"
                tooltip="Current average monthly rent per unit"
              />
              <InputField
                label="Market Rent"
                name="marketRentPerUnit"
                value={inputs.marketRentPerUnit}
                onChange={(v) => updateInput('marketRentPerUnit', v as number)}
                prefix="$"
                suffix="/mo"
                tooltip="Market-rate rent for comparable units"
              />
            </div>

            <SliderField
              label="Rent Growth"
              name="rentGrowthPercent"
              value={inputs.rentGrowthPercent}
              onChange={(v) => updateInput('rentGrowthPercent', v)}
              min={0}
              max={0.06}
              step={0.0025}
              tooltip="Annual rent increase assumption"
            />

            <InputField
              label="Other Income"
              name="otherIncomePerUnit"
              value={inputs.otherIncomePerUnit}
              onChange={(v) => updateInput('otherIncomePerUnit', v as number)}
              prefix="$"
              suffix="/mo"
              tooltip="Parking, laundry, pet fees, etc."
            />

            <div className="grid grid-cols-3 gap-4">
              <SliderField
                label="Vacancy"
                name="vacancyPercent"
                value={inputs.vacancyPercent}
                onChange={(v) => updateInput('vacancyPercent', v)}
                min={0}
                max={0.15}
                step={0.0025}
              />
              <SliderField
                label="Concessions"
                name="concessionsPercent"
                value={inputs.concessionsPercent}
                onChange={(v) => updateInput('concessionsPercent', v)}
                min={0}
                max={0.05}
                step={0.0025}
              />
              <SliderField
                label="Bad Debt"
                name="badDebtPercent"
                value={inputs.badDebtPercent}
                onChange={(v) => updateInput('badDebtPercent', v)}
                min={0}
                max={0.03}
                step={0.0025}
              />
            </div>
          </CollapsibleSection>
        </div>

        {/* Right Column */}
        <div className="space-y-4">
          {/* Financing Assumptions */}
          <CollapsibleSection title="Financing Assumptions">
            <SelectField
              label="Loan Type"
              name="loanType"
              value={inputs.loanType}
              onChange={(v) => updateInput('loanType', v as LoanType)}
              options={[
                { value: 'Agency', label: 'Agency (Fannie/Freddie)' },
                { value: 'CMBS', label: 'CMBS' },
                { value: 'Bridge', label: 'Bridge Loan' },
                { value: 'Bank', label: 'Bank/Portfolio' },
              ]}
            />

            <SliderField
              label="Loan-to-Value (LTV)"
              name="ltvPercent"
              value={inputs.ltvPercent}
              onChange={(v) => updateInput('ltvPercent', v)}
              min={0.5}
              max={0.85}
              step={0.0025}
            />

            <div className="p-3 bg-neutral-50 rounded">
              <div className="text-xs text-neutral-500 mb-1">Loan Amount</div>
              <div className="text-lg font-semibold text-neutral-900">
                ${loanAmount.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SliderField
                label="Interest Rate"
                name="interestRate"
                value={inputs.interestRate}
                onChange={(v) => updateInput('interestRate', v)}
                min={0.04}
                max={0.10}
                step={0.00125}
              />
              <InputField
                label="Loan Term"
                name="loanTerm"
                value={inputs.loanTerm}
                onChange={(v) => updateInput('loanTerm', v as number)}
                suffix="yrs"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <InputField
                label="Amortization"
                name="amortizationPeriod"
                value={inputs.amortizationPeriod}
                onChange={(v) => updateInput('amortizationPeriod', v as number)}
                suffix="yrs"
                tooltip="Loan amortization period (often 30 years)"
              />
              <InputField
                label="Interest-Only"
                name="interestOnlyPeriod"
                value={inputs.interestOnlyPeriod}
                onChange={(v) => updateInput('interestOnlyPeriod', v as number)}
                suffix="yrs"
                tooltip="Initial interest-only period"
              />
            </div>

            <SliderField
              label="Origination Fee"
              name="originationFeePercent"
              value={inputs.originationFeePercent}
              onChange={(v) => updateInput('originationFeePercent', v)}
              min={0}
              max={0.02}
              step={0.0025}
            />

            <SelectField
              label="Prepayment Penalty"
              name="prepaymentPenaltyType"
              value={inputs.prepaymentPenaltyType}
              onChange={(v) => updateInput('prepaymentPenaltyType', v as PrepaymentPenaltyType)}
              options={[
                { value: 'Yield Maintenance', label: 'Yield Maintenance' },
                { value: 'Defeasance', label: 'Defeasance' },
                { value: 'Step-Down', label: 'Step-Down' },
                { value: 'None', label: 'None' },
              ]}
            />
          </CollapsibleSection>

          {/* Operating Expenses */}
          <CollapsibleSection title="Operating Expenses (annual per unit)">
            <div className="grid grid-cols-2 gap-4">
              <InputField
                label="Property Tax"
                name="propertyTaxPerUnit"
                value={inputs.propertyTaxPerUnit}
                onChange={(v) => updateInput('propertyTaxPerUnit', v as number)}
                prefix="$"
              />
              <InputField
                label="Insurance"
                name="insurancePerUnit"
                value={inputs.insurancePerUnit}
                onChange={(v) => updateInput('insurancePerUnit', v as number)}
                prefix="$"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <InputField
                label="Utilities"
                name="utilitiesPerUnit"
                value={inputs.utilitiesPerUnit}
                onChange={(v) => updateInput('utilitiesPerUnit', v as number)}
                prefix="$"
              />
              <SliderField
                label="Management Fee"
                name="managementPercent"
                value={inputs.managementPercent}
                onChange={(v) => updateInput('managementPercent', v)}
                min={0.025}
                max={0.07}
                step={0.0025}
                suffix="%"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <InputField
                label="Repairs & Maint."
                name="repairsPerUnit"
                value={inputs.repairsPerUnit}
                onChange={(v) => updateInput('repairsPerUnit', v as number)}
                prefix="$"
              />
              <InputField
                label="Payroll"
                name="payrollPerUnit"
                value={inputs.payrollPerUnit}
                onChange={(v) => updateInput('payrollPerUnit', v as number)}
                prefix="$"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <InputField
                label="Marketing"
                name="marketingPerUnit"
                value={inputs.marketingPerUnit}
                onChange={(v) => updateInput('marketingPerUnit', v as number)}
                prefix="$"
              />
              <InputField
                label="Other Expenses"
                name="otherExpensesPerUnit"
                value={inputs.otherExpensesPerUnit}
                onChange={(v) => updateInput('otherExpensesPerUnit', v as number)}
                prefix="$"
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <InputField
                label="Turnover Costs"
                name="turnoverPerUnit"
                value={inputs.turnoverPerUnit}
                onChange={(v) => updateInput('turnoverPerUnit', v as number)}
                prefix="$"
                tooltip="Make-ready/unit turnover costs"
              />
              <InputField
                label="Contract Services"
                name="contractServicesPerUnit"
                value={inputs.contractServicesPerUnit}
                onChange={(v) => updateInput('contractServicesPerUnit', v as number)}
                prefix="$"
                tooltip="Landscaping, pest control, elevator, etc."
              />
              <InputField
                label="Admin/Legal/Security"
                name="administrativePerUnit"
                value={inputs.administrativePerUnit}
                onChange={(v) => updateInput('administrativePerUnit', v as number)}
                prefix="$"
                tooltip="Administrative, legal, and security expenses"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SliderField
                label="Expense Growth"
                name="expenseGrowthPercent"
                value={inputs.expenseGrowthPercent}
                onChange={(v) => updateInput('expenseGrowthPercent', v)}
                min={0}
                max={0.05}
                step={0.0025}
              />
              <InputField
                label="Reserves for Replacement"
                name="capitalReservePerUnit"
                value={inputs.capitalReservePerUnit}
                onChange={(v) => updateInput('capitalReservePerUnit', v as number)}
                prefix="$"
                tooltip="Annual reserves for replacement per unit"
              />
            </div>
          </CollapsibleSection>

          {/* Exit Assumptions */}
          <CollapsibleSection title="Exit Assumptions">
            <SliderField
              label="Hold Period"
              name="holdPeriod"
              value={inputs.holdPeriod}
              onChange={(v) => updateInput('holdPeriod', v)}
              min={3}
              max={10}
              step={1}
              suffix=" yrs"
            />

            <div className="grid grid-cols-2 gap-4">
              <SliderField
                label="Exit Cap Rate"
                name="exitCapRate"
                value={inputs.exitCapRate}
                onChange={(v) => updateInput('exitCapRate', v)}
                min={0.04}
                max={0.08}
                step={0.0025}
              />
              <SliderField
                label="Disposition Fee"
                name="dispositionFeePercent"
                value={inputs.dispositionFeePercent}
                onChange={(v) => updateInput('dispositionFeePercent', v)}
                min={0}
                max={0.03}
                step={0.0025}
              />
            </div>

            <SliderField
              label="Cap Rate Spread"
              name="capRateSpread"
              value={inputs.capRateSpread}
              onChange={(v) => updateInput('capRateSpread', v)}
              min={-0.01}
              max={0.01}
              step={0.0025}
              suffix="%"
              tooltip="Change from entry cap rate (negative = compression)"
            />
          </CollapsibleSection>
        </div>
      </div>
    </div>
  );
}
