import { Calendar, TrendingUp, TrendingDown, DollarSign, Wrench } from 'lucide-react';
import { useTransactionsWithMockFallback } from '@/hooks/api/useTransactions';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency, formatDate } from '@/lib/utils/formatters';

interface TransactionsTabProps {
  propertyId: string;
}

export function TransactionsTab({ propertyId }: TransactionsTabProps) {
  const { data: txnData } = useTransactionsWithMockFallback();
  const allTransactions = txnData?.transactions ?? [];
  const propertyTransactions = allTransactions.filter(
    (transaction) => transaction.propertyId === propertyId
  );

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'acquisition':
        return 'bg-blue-100 text-blue-800';
      case 'capital_improvement':
        return 'bg-orange-100 text-orange-800';
      case 'refinance':
        return 'bg-purple-100 text-purple-800';
      case 'distribution':
        return 'bg-green-100 text-green-800';
      case 'disposition':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'acquisition':
        return <TrendingUp className="w-4 h-4" />;
      case 'capital_improvement':
        return <Wrench className="w-4 h-4" />;
      case 'refinance':
        return <DollarSign className="w-4 h-4" />;
      case 'distribution':
        return <TrendingDown className="w-4 h-4" />;
      case 'disposition':
        return <TrendingDown className="w-4 h-4" />;
      default:
        return <Calendar className="w-4 h-4" />;
    }
  };

  const formatTypeName = (type: string) => {
    return type
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const totalTransactionValue = propertyTransactions.reduce(
    (sum, transaction) => sum + transaction.amount,
    0
  );

  const transactionsByType = propertyTransactions.reduce((acc, transaction) => {
    if (!acc[transaction.type]) {
      acc[transaction.type] = { count: 0, total: 0 };
    }
    acc[transaction.type].count++;
    acc[transaction.type].total += transaction.amount;
    return acc;
  }, {} as Record<string, { count: number; total: number }>);

  return (
    <div className="p-6 space-y-6">
      {/* Transaction Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Total Transactions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{propertyTransactions.length}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Total Value</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(totalTransactionValue)}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">First Transaction</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-semibold">
              {propertyTransactions.length > 0
                ? formatDate(
                    new Date(
                      Math.min(
                        ...propertyTransactions.map((t) => new Date(t.date).getTime())
                      )
                    )
                  )
                : 'N/A'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Last Transaction</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-semibold">
              {propertyTransactions.length > 0
                ? formatDate(
                    new Date(
                      Math.max(
                        ...propertyTransactions.map((t) => new Date(t.date).getTime())
                      )
                    )
                  )
                : 'N/A'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Transaction Breakdown by Type */}
      <Card>
        <CardHeader>
          <CardTitle>Transaction Breakdown by Type</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(transactionsByType).map(([type, stats]) => (
              <div key={type} className="border rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  {getTypeIcon(type)}
                  <span className="font-medium">{formatTypeName(type)}</span>
                </div>
                <div className="space-y-1">
                  <div className="text-sm text-gray-600">
                    Count: <span className="font-semibold text-gray-900">{stats.count}</span>
                  </div>
                  <div className="text-sm text-gray-600">
                    Total: <span className="font-semibold text-gray-900">{formatCurrency(stats.total)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Transaction List */}
      <Card>
        <CardHeader>
          <CardTitle>Transaction History</CardTitle>
        </CardHeader>
        <CardContent>
          {propertyTransactions.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No transactions found for this property.
            </div>
          ) : (
            <div className="space-y-3">
              {propertyTransactions
                .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
                .map((transaction) => (
                  <div
                    key={transaction.id}
                    className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className={`p-2 rounded-lg ${getTypeColor(transaction.type)}`}>
                        {getTypeIcon(transaction.type)}
                      </div>
                      <div>
                        <div className="font-medium text-gray-900">
                          {transaction.description}
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-sm text-gray-600">
                            {formatDate(transaction.date)}
                          </span>
                          <span className="text-gray-300">•</span>
                          <span
                            className={`text-xs px-2 py-0.5 rounded-full ${getTypeColor(
                              transaction.type
                            )}`}
                          >
                            {formatTypeName(transaction.type)}
                          </span>
                          {transaction.category && (
                            <>
                              <span className="text-gray-300">•</span>
                              <span className="text-xs text-gray-600">
                                {transaction.category}
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-semibold text-gray-900">
                        {formatCurrency(transaction.amount)}
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
