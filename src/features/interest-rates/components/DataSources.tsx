import { ExternalLink, Database, Clock, CheckCircle } from 'lucide-react';
import type { RateDataSource } from '@/data/mockInterestRates';
import { realEstateLendingContext } from '@/data/mockInterestRates';

interface DataSourcesProps {
  sources: RateDataSource[];
}

export function DataSources({ sources }: DataSourcesProps) {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold text-neutral-900">Data Sources</h3>
        <p className="text-sm text-neutral-500">
          Official sources for interest rate data and market information
        </p>
      </div>

      {/* Primary Sources */}
      <div>
        <h4 className="text-sm font-medium text-neutral-700 mb-4 flex items-center gap-2">
          <Database className="w-4 h-4" />
          Official Data Sources
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sources.map(source => (
            <div
              key={source.id}
              className="bg-white rounded-lg border border-neutral-200 p-5 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h5 className="font-semibold text-neutral-900">{source.name}</h5>
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1 mt-1"
                  >
                    {source.url.replace('https://', '').replace('www.', '')}
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <div className="flex items-center gap-1 text-xs text-neutral-500 bg-neutral-100 px-2 py-1 rounded-full">
                  <Clock className="w-3 h-3" />
                  {source.updateFrequency}
                </div>
              </div>

              <p className="text-sm text-neutral-600 mb-4">{source.description}</p>

              <div className="flex flex-wrap gap-2">
                {source.dataTypes.map(dataType => (
                  <span
                    key={dataType}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-primary-50 text-primary-700 text-xs rounded-full"
                  >
                    <CheckCircle className="w-3 h-3" />
                    {dataType}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Real Estate Lending Context */}
      <div className="bg-gradient-to-br from-primary-50 to-blue-50 rounded-lg p-6 border border-primary-100">
        <h4 className="text-sm font-medium text-primary-800 mb-4 flex items-center gap-2">
          <Database className="w-4 h-4" />
          Real Estate Lending Context
        </h4>

        <p className="text-sm text-neutral-600 mb-4">
          Understanding how benchmark rates translate to commercial real estate financing:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {Object.entries(realEstateLendingContext.typicalSpreads).map(([key, spread]) => (
            <div key={key} className="bg-white rounded-lg p-4 border border-primary-100">
              <div className="flex items-center justify-between mb-2">
                <h5 className="font-medium text-neutral-900">{spread.name}</h5>
                <span className="text-xs text-neutral-500">vs {spread.benchmark}</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-primary-700">
                  +{'spreadOverTreasury' in spread
                    ? (spread.spreadOverTreasury * 100).toFixed(0)
                    : 'spreadOverSOFR' in spread
                    ? (spread.spreadOverSOFR * 100).toFixed(0)
                    : (spread.spreadOverPrime * 100).toFixed(0)
                  }
                </span>
                <span className="text-sm text-neutral-500">bps typical spread</span>
              </div>
            </div>
          ))}
        </div>

        <div className="bg-white rounded-lg p-4 border border-primary-100">
          <h5 className="font-medium text-neutral-900 mb-3">Current Indicative Rates</h5>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-xs text-neutral-500">Multifamily Perm</p>
              <p className="text-lg font-semibold text-neutral-900">
                {realEstateLendingContext.currentIndicativeRates.multifamilyPerm.toFixed(2)}%
              </p>
            </div>
            <div>
              <p className="text-xs text-neutral-500">Multifamily Bridge</p>
              <p className="text-lg font-semibold text-neutral-900">
                {realEstateLendingContext.currentIndicativeRates.multifamilyBridge.toFixed(2)}%
              </p>
            </div>
            <div>
              <p className="text-xs text-neutral-500">Commercial Perm</p>
              <p className="text-lg font-semibold text-neutral-900">
                {realEstateLendingContext.currentIndicativeRates.commercialPerm.toFixed(2)}%
              </p>
            </div>
            <div>
              <p className="text-xs text-neutral-500">Construction</p>
              <p className="text-lg font-semibold text-neutral-900">
                {realEstateLendingContext.currentIndicativeRates.construction.toFixed(2)}%
              </p>
            </div>
          </div>
          <p className="text-xs text-neutral-500 mt-3 italic">
            * Indicative rates only. Actual rates depend on property type, location, sponsorship, and market conditions.
          </p>
        </div>
      </div>

      {/* API Integration Info */}
      <div className="bg-neutral-50 rounded-lg p-6 border border-neutral-200">
        <h4 className="text-sm font-medium text-neutral-700 mb-4">API Integration</h4>
        <p className="text-sm text-neutral-600 mb-4">
          For production deployment, the following APIs can be integrated for real-time data:
        </p>
        <div className="space-y-3">
          <div className="flex items-start gap-3">
            <div className="w-2 h-2 rounded-full bg-green-500 mt-1.5" />
            <div>
              <p className="text-sm font-medium text-neutral-900">FRED API (St. Louis Fed)</p>
              <p className="text-xs text-neutral-500">Free API key available. Supports Treasury yields, Fed Funds, SOFR, and 700K+ economic series.</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-2 h-2 rounded-full bg-green-500 mt-1.5" />
            <div>
              <p className="text-sm font-medium text-neutral-900">Treasury.gov Daily Yield Curve</p>
              <p className="text-xs text-neutral-500">XML/CSV downloads available daily. No API key required.</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-2 h-2 rounded-full bg-yellow-500 mt-1.5" />
            <div>
              <p className="text-sm font-medium text-neutral-900">CME Term SOFR</p>
              <p className="text-xs text-neutral-500">Requires CME DataMine subscription for real-time Term SOFR rates.</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-2 h-2 rounded-full bg-yellow-500 mt-1.5" />
            <div>
              <p className="text-sm font-medium text-neutral-900">Mortgage Rate APIs</p>
              <p className="text-xs text-neutral-500">Freddie Mac PMMS (free), Bankrate (subscription), or Zillow API for mortgage rates.</p>
            </div>
          </div>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="text-xs text-neutral-500 p-4 bg-neutral-100 rounded-lg">
        <p className="font-medium mb-1">Disclaimer</p>
        <p>
          Interest rate data is provided for informational purposes only. Rates shown are indicative and may not reflect
          real-time market conditions. Always consult with a qualified financial professional before making investment
          or financing decisions. Past performance does not guarantee future results.
        </p>
      </div>
    </div>
  );
}
