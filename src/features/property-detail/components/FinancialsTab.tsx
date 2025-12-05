import { Calendar, DollarSign, TrendingUp } from 'lucide-react';
import type { Property } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency, formatPercent, formatDate } from '@/lib/utils/formatters';

interface FinancialsTabProps {
  property: Property;
}

export function FinancialsTab({ property }: FinancialsTabProps) {
  return (
    <div className="p-6 space-y-6">
      {/* Acquisition Details */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-primary-600" />
            <CardTitle>Acquisition Details</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div className="text-sm text-gray-600 mb-1">Acquisition Date</div>
              <div className="text-lg font-semibold">{formatDate(property.acquisition.date)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Purchase Price</div>
              <div className="text-lg font-semibold">{formatCurrency(property.acquisition.purchasePrice)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Price Per Unit</div>
              <div className="text-lg font-semibold">{formatCurrency(property.acquisition.pricePerUnit)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Closing Costs</div>
              <div className="text-lg font-semibold">{formatCurrency(property.acquisition.closingCosts)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Acquisition Fee</div>
              <div className="text-lg font-semibold">{formatCurrency(property.acquisition.acquisitionFee)}</div>
            </div>
            <div className="bg-primary-50 p-4 rounded-lg">
              <div className="text-sm text-primary-600 mb-1">Total Invested</div>
              <div className="text-xl font-bold text-primary-900">{formatCurrency(property.acquisition.totalInvested)}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Financing Details */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-accent-600" />
            <CardTitle>Financing Details</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div className="text-sm text-gray-600 mb-1">Loan Amount</div>
              <div className="text-lg font-semibold">{formatCurrency(property.financing.loanAmount)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Loan-to-Value (LTV)</div>
              <div className="text-lg font-semibold">{formatPercent(property.financing.loanToValue)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Interest Rate</div>
              <div className="text-lg font-semibold">{formatPercent(property.financing.interestRate)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Loan Term</div>
              <div className="text-lg font-semibold">{property.financing.loanTerm} years</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Amortization Period</div>
              <div className="text-lg font-semibold">{property.financing.amortization} years</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Monthly Payment</div>
              <div className="text-lg font-semibold">{formatCurrency(property.financing.monthlyPayment)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Lender</div>
              <div className="text-lg font-semibold">{property.financing.lender}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Maturity Date</div>
              <div className="text-lg font-semibold">{formatDate(property.financing.maturityDate)}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Valuation */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-green-600" />
            <CardTitle>Current Valuation</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-green-50 p-4 rounded-lg">
              <div className="text-sm text-green-600 mb-1">Current Value</div>
              <div className="text-2xl font-bold text-green-900">{formatCurrency(property.valuation.currentValue)}</div>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <div className="text-sm text-green-600 mb-1">Appreciation Since Acquisition</div>
              <div className="text-2xl font-bold text-green-900">+{formatPercent(property.valuation.appreciationSinceAcquisition)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Last Appraisal Date</div>
              <div className="text-lg font-semibold">{formatDate(property.valuation.lastAppraisalDate)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Cap Rate</div>
              <div className="text-lg font-semibold">{formatPercent(property.valuation.capRate)}</div>
            </div>
            <div className="col-span-2">
              <div className="text-sm text-gray-600 mb-1">Value Change</div>
              <div className="text-lg font-semibold text-green-600">
                +{formatCurrency(property.valuation.currentValue - property.acquisition.purchasePrice)}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
