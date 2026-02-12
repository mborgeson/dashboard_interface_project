import { ExternalLink, Database, Clock, CheckCircle } from 'lucide-react';
import type { RateDataSource } from '../types';

interface DataSourcesProps {
  sources: RateDataSource[];
}

// Typical CRE lending spreads — static industry reference data
const typicalSpreads = [
  { key: 'multifamilyPerm', name: 'Multifamily Permanent', spreadBps: 150, benchmark: '10Y Treasury' },
  { key: 'multifamilyBridge', name: 'Multifamily Bridge', spreadBps: 300, benchmark: 'SOFR' },
  { key: 'commercialPerm', name: 'Commercial Permanent', spreadBps: 175, benchmark: '10Y Treasury' },
  { key: 'construction', name: 'Construction', spreadBps: 50, benchmark: 'Prime Rate' },
];

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
          {typicalSpreads.map((spread) => (
            <div key={spread.key} className="bg-white rounded-lg p-4 border border-primary-100">
              <div className="flex items-center justify-between mb-2">
                <h5 className="font-medium text-neutral-900">{spread.name}</h5>
                <span className="text-xs text-neutral-500">vs {spread.benchmark}</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-primary-700">
                  +{spread.spreadBps}
                </span>
                <span className="text-sm text-neutral-500">bps typical spread</span>
              </div>
            </div>
          ))}
        </div>

        <p className="text-xs text-neutral-500 italic">
          * Typical spreads only. Actual rates depend on property type, location, sponsorship, and market conditions.
          See the Lending Context page for current indicative rates calculated from live benchmarks.
        </p>
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
