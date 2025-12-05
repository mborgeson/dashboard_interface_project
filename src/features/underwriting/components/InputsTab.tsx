import type { UnderwritingInputs } from '@/types';
import { Label } from '@/components/ui/label';

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
}: {
  label: string;
  name: string;
  value: number | string;
  onChange: (value: number | string) => void;
  type?: 'number' | 'text';
  prefix?: string;
  suffix?: string;
  step?: string;
}) {
  return (
    <div className="space-y-1">
      <Label htmlFor={name} className="text-sm text-neutral-600">
        {label}
      </Label>
      <div className="relative">
        {prefix && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500">
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
          className={`w-full rounded-md border border-neutral-300 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 ${
            prefix ? 'pl-7' : 'pl-3'
          } ${suffix ? 'pr-12' : 'pr-3'}`}
        />
        {suffix && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500">
            {suffix}
          </span>
        )}
      </div>
    </div>
  );
}

function SectionHeader({ title }: { title: string }) {
  return (
    <h4 className="text-sm font-semibold text-neutral-800 border-b border-neutral-200 pb-2 mb-3">
      {title}
    </h4>
  );
}

export function InputsTab({ inputs, updateInput }: InputsTabProps) {
  return (
    <div className="grid grid-cols-3 gap-6 max-h-[60vh] overflow-y-auto pr-2">
      {/* Property Information */}
      <div className="space-y-4">
        <SectionHeader title="Property Information" />
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
        <InputField
          label="Units"
          name="units"
          value={inputs.units}
          onChange={(v) => updateInput('units', v as number)}
        />
        <InputField
          label="Square Feet"
          name="squareFeet"
          value={inputs.squareFeet}
          onChange={(v) => updateInput('squareFeet', v as number)}
        />
        <InputField
          label="Year Built"
          name="yearBuilt"
          value={inputs.yearBuilt}
          onChange={(v) => updateInput('yearBuilt', v as number)}
        />
      </div>

      {/* Financial Assumptions */}
      <div className="space-y-4">
        <SectionHeader title="Financial Assumptions" />
        <InputField
          label="Purchase Price"
          name="purchasePrice"
          value={inputs.purchasePrice}
          onChange={(v) => updateInput('purchasePrice', v as number)}
          prefix="$"
        />
        <InputField
          label="Down Payment"
          name="downPaymentPercent"
          value={(inputs.downPaymentPercent * 100).toFixed(0)}
          onChange={(v) => updateInput('downPaymentPercent', (v as number) / 100)}
          suffix="%"
        />
        <InputField
          label="Interest Rate"
          name="interestRate"
          value={(inputs.interestRate * 100).toFixed(2)}
          onChange={(v) => updateInput('interestRate', (v as number) / 100)}
          suffix="%"
          step="0.125"
        />
        <InputField
          label="Loan Term (Years)"
          name="loanTerm"
          value={inputs.loanTerm}
          onChange={(v) => updateInput('loanTerm', v as number)}
        />
        <InputField
          label="Closing Costs"
          name="closingCostsPercent"
          value={(inputs.closingCostsPercent * 100).toFixed(1)}
          onChange={(v) => updateInput('closingCostsPercent', (v as number) / 100)}
          suffix="%"
        />

        <SectionHeader title="Exit Assumptions" />
        <InputField
          label="Hold Period (Years)"
          name="holdPeriod"
          value={inputs.holdPeriod}
          onChange={(v) => updateInput('holdPeriod', v as number)}
        />
        <InputField
          label="Exit Cap Rate"
          name="exitCapRate"
          value={(inputs.exitCapRate * 100).toFixed(2)}
          onChange={(v) => updateInput('exitCapRate', (v as number) / 100)}
          suffix="%"
          step="0.25"
        />
        <InputField
          label="Selling Costs"
          name="sellingCostsPercent"
          value={(inputs.sellingCostsPercent * 100).toFixed(1)}
          onChange={(v) => updateInput('sellingCostsPercent', (v as number) / 100)}
          suffix="%"
        />
      </div>

      {/* Income & Expenses */}
      <div className="space-y-4">
        <SectionHeader title="Income Projections" />
        <InputField
          label="Current Rent/Unit"
          name="currentRentPerUnit"
          value={inputs.currentRentPerUnit}
          onChange={(v) => updateInput('currentRentPerUnit', v as number)}
          prefix="$"
        />
        <InputField
          label="Rent Growth"
          name="rentGrowthPercent"
          value={(inputs.rentGrowthPercent * 100).toFixed(1)}
          onChange={(v) => updateInput('rentGrowthPercent', (v as number) / 100)}
          suffix="%"
        />
        <InputField
          label="Other Income/Unit"
          name="otherIncomePerUnit"
          value={inputs.otherIncomePerUnit}
          onChange={(v) => updateInput('otherIncomePerUnit', v as number)}
          prefix="$"
        />
        <InputField
          label="Vacancy"
          name="vacancyPercent"
          value={(inputs.vacancyPercent * 100).toFixed(1)}
          onChange={(v) => updateInput('vacancyPercent', (v as number) / 100)}
          suffix="%"
        />

        <SectionHeader title="Operating Expenses (per unit/yr)" />
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
        <InputField
          label="Management Fee"
          name="managementPercent"
          value={(inputs.managementPercent * 100).toFixed(1)}
          onChange={(v) => updateInput('managementPercent', (v as number) / 100)}
          suffix="%"
        />
        <InputField
          label="Repairs & Maintenance"
          name="repairsPercent"
          value={(inputs.repairsPercent * 100).toFixed(1)}
          onChange={(v) => updateInput('repairsPercent', (v as number) / 100)}
          suffix="%"
        />
      </div>
    </div>
  );
}
