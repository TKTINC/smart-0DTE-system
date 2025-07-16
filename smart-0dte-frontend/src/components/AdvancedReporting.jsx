import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Progress } from './ui/progress';
import { Separator } from './ui/separator';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  PieChart, 
  BarChart3, 
  Download, 
  Calendar,
  AlertTriangle,
  CheckCircle,
  Target,
  Shield,
  Zap
} from 'lucide-react';
import { LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart as RechartsPieChart, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const AdvancedReporting = () => {
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedPeriod, setSelectedPeriod] = useState('monthly');
  const [taxData, setTaxData] = useState(null);
  const [performanceMetrics, setPerformanceMetrics] = useState(null);

  // Mock data for demonstration
  useEffect(() => {
    const fetchReportData = async () => {
      setLoading(true);
      
      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Mock comprehensive report data
      const mockData = {
        report_id: "RPT_20241206_001",
        generated_at: new Date().toISOString(),
        period_start: "2024-01-01T00:00:00Z",
        period_end: "2024-12-06T23:59:59Z",
        performance_summary: {
          total_trades: 342,
          win_rate: 68.5,
          total_pnl: 15847.32,
          sharpe_ratio: 1.84,
          max_drawdown: -8.2
        },
        tax_summary: {
          short_term_gains: 8945.67,
          long_term_gains: 6901.65,
          tax_efficiency_score: 72.3
        },
        risk_summary: {
          var_95: -2.1,
          maximum_drawdown: -8.2,
          correlation_spy: 0.73
        },
        strategy_performance: [
          { strategy: "Mean Reversion", total_pnl: 6234.56, win_rate: 71.2, trades: 128 },
          { strategy: "Momentum Breakout", total_pnl: 4892.33, win_rate: 65.8, trades: 97 },
          { strategy: "Correlation Breakdown", total_pnl: 3456.78, win_rate: 69.4, trades: 85 },
          { strategy: "VIX Hedging", total_pnl: 1263.65, win_rate: 58.3, trades: 32 }
        ],
        recommendations: [
          "Consider increasing position size during low volatility periods",
          "Implement stricter stop-loss rules for momentum strategies",
          "Hold positions longer to improve tax efficiency",
          "Diversify across more ETF symbols for better risk distribution"
        ],
        charts_data: {
          equity_curve: [
            { date: "2024-01", value: 50000 },
            { date: "2024-02", value: 52150 },
            { date: "2024-03", value: 51890 },
            { date: "2024-04", value: 54230 },
            { date: "2024-05", value: 53980 },
            { date: "2024-06", value: 56120 },
            { date: "2024-07", value: 57450 },
            { date: "2024-08", value: 56890 },
            { date: "2024-09", value: 59340 },
            { date: "2024-10", value: 61230 },
            { date: "2024-11", value: 63890 },
            { date: "2024-12", value: 65847 }
          ],
          drawdown_chart: [
            { date: "2024-01", drawdown: 0 },
            { date: "2024-02", drawdown: -1.2 },
            { date: "2024-03", drawdown: -2.8 },
            { date: "2024-04", drawdown: -0.5 },
            { date: "2024-05", drawdown: -3.1 },
            { date: "2024-06", drawdown: -1.8 },
            { date: "2024-07", drawdown: -0.9 },
            { date: "2024-08", drawdown: -4.2 },
            { date: "2024-09", drawdown: -2.1 },
            { date: "2024-10", drawdown: -1.5 },
            { date: "2024-11", drawdown: -0.8 },
            { date: "2024-12", drawdown: -8.2 }
          ],
          monthly_returns: [
            { month: "Jan", return: 4.3, benchmark: 2.1 },
            { month: "Feb", return: -1.2, benchmark: 1.8 },
            { month: "Mar", return: 4.5, benchmark: 3.2 },
            { month: "Apr", return: -0.9, benchmark: -1.1 },
            { month: "May", return: 3.8, benchmark: 2.9 },
            { month: "Jun", return: 2.4, benchmark: 1.7 },
            { month: "Jul", return: -1.8, benchmark: -0.5 },
            { month: "Aug", return: 4.2, benchmark: 2.8 },
            { month: "Sep", return: 2.1, benchmark: 1.9 },
            { month: "Oct", return: 3.0, benchmark: 2.4 },
            { month: "Nov", return: -2.1, benchmark: -1.8 },
            { month: "Dec", return: 1.8, benchmark: 1.2 }
          ]
        }
      };

      const mockTaxData = {
        short_term_gains: 8945.67,
        long_term_gains: 6901.65,
        total_gains: 15847.32,
        wash_sale_adjustments: 234.56,
        realized_gains: 15612.76,
        unrealized_gains: 2345.67,
        tax_efficiency_score: 72.3,
        recommendations: [
          "Hold positions longer to qualify for long-term capital gains treatment",
          "Avoid repurchasing the same security within 30 days of a loss",
          "Consider harvesting losses in December for tax optimization",
          "Focus on ETF trading for better tax efficiency"
        ]
      };

      const mockPerformanceMetrics = {
        total_trades: 342,
        win_rate: 68.5,
        total_pnl: 15847.32,
        profit_factor: 2.34,
        sharpe_ratio: 1.84,
        max_drawdown: -8.2,
        total_return: 31.7,
        annualized_return: 28.4,
        volatility: 15.6,
        average_win: 156.78,
        average_loss: -89.45,
        largest_win: 892.34,
        largest_loss: -456.78
      };

      setReportData(mockData);
      setTaxData(mockTaxData);
      setPerformanceMetrics(mockPerformanceMetrics);
      setLoading(false);
    };

    fetchReportData();
  }, [selectedPeriod]);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value);
  };

  const formatPercentage = (value) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getPerformanceColor = (value) => {
    return value >= 0 ? 'text-green-600' : 'text-red-600';
  };

  const getPerformanceBadgeVariant = (value) => {
    return value >= 0 ? 'default' : 'destructive';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Generating comprehensive report...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold">Advanced Performance Report</h2>
          <p className="text-gray-600 mt-1">
            Comprehensive analytics with tax optimization insights
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            <Calendar className="h-4 w-4 mr-2" />
            Change Period
          </Button>
          <Button size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export Report
          </Button>
        </div>
      </div>

      {/* Key Performance Indicators */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total P&L</p>
                <p className={`text-2xl font-bold ${getPerformanceColor(reportData.performance_summary.total_pnl)}`}>
                  {formatCurrency(reportData.performance_summary.total_pnl)}
                </p>
              </div>
              <DollarSign className="h-8 w-8 text-green-600" />
            </div>
            <div className="mt-2">
              <Badge variant={getPerformanceBadgeVariant(reportData.performance_summary.total_pnl)}>
                {formatPercentage(31.7)} YTD
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Win Rate</p>
                <p className="text-2xl font-bold text-blue-600">
                  {reportData.performance_summary.win_rate}%
                </p>
              </div>
              <Target className="h-8 w-8 text-blue-600" />
            </div>
            <div className="mt-2">
              <Progress value={reportData.performance_summary.win_rate} className="h-2" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Sharpe Ratio</p>
                <p className="text-2xl font-bold text-purple-600">
                  {reportData.performance_summary.sharpe_ratio}
                </p>
              </div>
              <TrendingUp className="h-8 w-8 text-purple-600" />
            </div>
            <div className="mt-2">
              <Badge variant="secondary">Excellent</Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Max Drawdown</p>
                <p className="text-2xl font-bold text-red-600">
                  {reportData.performance_summary.max_drawdown}%
                </p>
              </div>
              <TrendingDown className="h-8 w-8 text-red-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline">Within Limits</Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="performance" className="space-y-4">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="tax">Tax Analysis</TabsTrigger>
          <TabsTrigger value="risk">Risk Metrics</TabsTrigger>
          <TabsTrigger value="strategies">Strategies</TabsTrigger>
          <TabsTrigger value="recommendations">Insights</TabsTrigger>
        </TabsList>

        {/* Performance Tab */}
        <TabsContent value="performance" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Equity Curve */}
            <Card>
              <CardHeader>
                <CardTitle>Equity Curve</CardTitle>
                <CardDescription>Portfolio value over time</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={reportData.charts_data.equity_curve}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip formatter={(value) => formatCurrency(value)} />
                    <Area 
                      type="monotone" 
                      dataKey="value" 
                      stroke="#3b82f6" 
                      fill="#3b82f6" 
                      fillOpacity={0.1}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Drawdown Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Drawdown Analysis</CardTitle>
                <CardDescription>Portfolio drawdown periods</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={reportData.charts_data.drawdown_chart}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip formatter={(value) => `${value}%`} />
                    <Area 
                      type="monotone" 
                      dataKey="drawdown" 
                      stroke="#ef4444" 
                      fill="#ef4444" 
                      fillOpacity={0.2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Monthly Returns */}
          <Card>
            <CardHeader>
              <CardTitle>Monthly Returns vs Benchmark</CardTitle>
              <CardDescription>Performance comparison with SPY benchmark</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={reportData.charts_data.monthly_returns}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip formatter={(value) => `${value}%`} />
                  <Legend />
                  <Bar dataKey="return" fill="#3b82f6" name="Portfolio" />
                  <Bar dataKey="benchmark" fill="#94a3b8" name="SPY Benchmark" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Performance Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="text-center">
                  <p className="text-sm text-gray-600">Total Trades</p>
                  <p className="text-xl font-bold">{performanceMetrics.total_trades}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="text-center">
                  <p className="text-sm text-gray-600">Profit Factor</p>
                  <p className="text-xl font-bold text-green-600">{performanceMetrics.profit_factor}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="text-center">
                  <p className="text-sm text-gray-600">Average Win</p>
                  <p className="text-xl font-bold text-green-600">{formatCurrency(performanceMetrics.average_win)}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="text-center">
                  <p className="text-sm text-gray-600">Average Loss</p>
                  <p className="text-xl font-bold text-red-600">{formatCurrency(performanceMetrics.average_loss)}</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Tax Analysis Tab */}
        <TabsContent value="tax" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Tax Summary */}
            <Card>
              <CardHeader>
                <CardTitle>Tax Summary</CardTitle>
                <CardDescription>Capital gains breakdown and tax efficiency</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Short-term Gains</span>
                  <span className="font-bold text-orange-600">{formatCurrency(taxData.short_term_gains)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Long-term Gains</span>
                  <span className="font-bold text-green-600">{formatCurrency(taxData.long_term_gains)}</span>
                </div>
                <Separator />
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Total Realized Gains</span>
                  <span className="font-bold">{formatCurrency(taxData.realized_gains)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Unrealized Gains</span>
                  <span className="font-bold text-blue-600">{formatCurrency(taxData.unrealized_gains)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Wash Sale Adjustments</span>
                  <span className="font-bold text-red-600">{formatCurrency(taxData.wash_sale_adjustments)}</span>
                </div>
              </CardContent>
            </Card>

            {/* Tax Efficiency Score */}
            <Card>
              <CardHeader>
                <CardTitle>Tax Efficiency Score</CardTitle>
                <CardDescription>How tax-optimized is your trading?</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center mb-4">
                  <div className="text-4xl font-bold text-blue-600 mb-2">
                    {taxData.tax_efficiency_score}/100
                  </div>
                  <Progress value={taxData.tax_efficiency_score} className="h-3" />
                  <p className="text-sm text-gray-600 mt-2">
                    {taxData.tax_efficiency_score >= 80 ? 'Excellent' : 
                     taxData.tax_efficiency_score >= 60 ? 'Good' : 
                     taxData.tax_efficiency_score >= 40 ? 'Fair' : 'Needs Improvement'}
                  </p>
                </div>
                
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <span className="text-sm">Long-term gains optimization</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-orange-600" />
                    <span className="text-sm">Wash sale rule compliance</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <span className="text-sm">ETF tax efficiency</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Tax Recommendations */}
          <Card>
            <CardHeader>
              <CardTitle>Tax Optimization Recommendations</CardTitle>
              <CardDescription>Actionable insights to improve tax efficiency</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {taxData.recommendations.map((recommendation, index) => (
                  <div key={index} className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
                    <Zap className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                    <p className="text-sm">{recommendation}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Tax Export */}
          <Card>
            <CardHeader>
              <CardTitle>Export Tax Data</CardTitle>
              <CardDescription>Download tax reports for your accountant or tax software</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Button variant="outline">
                  <Download className="h-4 w-4 mr-2" />
                  Export CSV
                </Button>
                <Button variant="outline">
                  <Download className="h-4 w-4 mr-2" />
                  Export PDF
                </Button>
                <Button variant="outline">
                  <Download className="h-4 w-4 mr-2" />
                  TurboTax Format
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Risk Metrics Tab */}
        <TabsContent value="risk" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Value at Risk</CardTitle>
                <CardDescription>95% confidence level</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center">
                  <div className="text-3xl font-bold text-red-600 mb-2">
                    {reportData.risk_summary.var_95}%
                  </div>
                  <p className="text-sm text-gray-600">Daily VaR</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Maximum Drawdown</CardTitle>
                <CardDescription>Worst peak-to-trough decline</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center">
                  <div className="text-3xl font-bold text-red-600 mb-2">
                    {reportData.risk_summary.maximum_drawdown}%
                  </div>
                  <p className="text-sm text-gray-600">Peak decline</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>SPY Correlation</CardTitle>
                <CardDescription>Market correlation</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center">
                  <div className="text-3xl font-bold text-blue-600 mb-2">
                    {reportData.risk_summary.correlation_spy}
                  </div>
                  <p className="text-sm text-gray-600">Correlation coefficient</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Strategies Tab */}
        <TabsContent value="strategies" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Strategy Performance Breakdown</CardTitle>
              <CardDescription>Performance analysis by trading strategy</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {reportData.strategy_performance.map((strategy, index) => (
                  <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex-1">
                      <h4 className="font-semibold">{strategy.strategy}</h4>
                      <p className="text-sm text-gray-600">{strategy.trades} trades</p>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className="font-semibold">{formatCurrency(strategy.total_pnl)}</p>
                        <p className="text-sm text-gray-600">{strategy.win_rate}% win rate</p>
                      </div>
                      <Badge variant={strategy.total_pnl >= 0 ? 'default' : 'destructive'}>
                        {formatPercentage((strategy.total_pnl / 50000) * 100)}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Recommendations Tab */}
        <TabsContent value="recommendations" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>AI-Powered Insights & Recommendations</CardTitle>
              <CardDescription>Actionable recommendations to improve your trading performance</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {reportData.recommendations.map((recommendation, index) => (
                  <div key={index} className="flex items-start gap-3 p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg">
                    <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold">
                      {index + 1}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">{recommendation}</p>
                    </div>
                    <Button size="sm" variant="outline">
                      Apply
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
              <CardDescription>Common optimization actions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Button variant="outline" className="h-auto p-4 flex flex-col items-start">
                  <Shield className="h-5 w-5 mb-2" />
                  <span className="font-semibold">Optimize Risk Settings</span>
                  <span className="text-sm text-gray-600">Adjust position sizing and stop losses</span>
                </Button>
                <Button variant="outline" className="h-auto p-4 flex flex-col items-start">
                  <PieChart className="h-5 w-5 mb-2" />
                  <span className="font-semibold">Rebalance Strategies</span>
                  <span className="text-sm text-gray-600">Adjust strategy allocations</span>
                </Button>
                <Button variant="outline" className="h-auto p-4 flex flex-col items-start">
                  <BarChart3 className="h-5 w-5 mb-2" />
                  <span className="font-semibold">Tax Loss Harvesting</span>
                  <span className="text-sm text-gray-600">Optimize for tax efficiency</span>
                </Button>
                <Button variant="outline" className="h-auto p-4 flex flex-col items-start">
                  <Target className="h-5 w-5 mb-2" />
                  <span className="font-semibold">Update Targets</span>
                  <span className="text-sm text-gray-600">Adjust profit and loss targets</span>
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AdvancedReporting;

