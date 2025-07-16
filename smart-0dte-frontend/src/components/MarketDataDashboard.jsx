import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Progress } from './ui/progress';
import { Separator } from './ui/separator';
import { ScrollArea } from './ui/scroll-area';
import { 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  BarChart3, 
  Zap, 
  Target,
  RefreshCw,
  Download,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';

const MarketDataDashboard = () => {
  const [marketData, setMarketData] = useState({
    SPY: { price: 485.67, change: 2.34, changePercent: 0.48, volume: 45700000, bid: 485.65, ask: 485.69 },
    QQQ: { price: 412.89, change: -1.24, changePercent: -0.30, volume: 32100000, bid: 412.87, ask: 412.91 },
    IWM: { price: 218.45, change: 0.87, changePercent: 0.40, volume: 18900000, bid: 218.43, ask: 218.47 }
  });

  const [vixData, setVixData] = useState({
    level: 16.8,
    change: -0.45,
    changePercent: -2.6,
    regime: 'low',
    termStructure: {
      'VIX9D': 15.9,
      'VIX': 16.8,
      'VIX3M': 17.6,
      'VIX6M': 18.4
    }
  });

  const [correlationData, setCorrelationData] = useState({
    spyQqq: 0.85,
    spyIwm: 0.72,
    qqIwm: 0.68,
    spyVix: -0.65,
    qqVix: -0.58,
    iwmVix: -0.52,
    regimeChangeProbability: 0.25
  });

  const [optionsData, setOptionsData] = useState({
    SPY: {
      atmCall: { strike: 485, bid: 2.45, ask: 2.48, iv: 0.18, delta: 0.52, volume: 1250 },
      atmPut: { strike: 485, bid: 2.42, ask: 2.45, iv: 0.19, delta: -0.48, volume: 980 }
    },
    QQQ: {
      atmCall: { strike: 413, bid: 3.12, ask: 3.15, iv: 0.22, delta: 0.51, volume: 890 },
      atmPut: { strike: 413, bid: 3.08, ask: 3.11, iv: 0.23, delta: -0.49, volume: 720 }
    },
    IWM: {
      atmCall: { strike: 218, bid: 1.89, ask: 1.92, iv: 0.28, delta: 0.50, volume: 450 },
      atmPut: { strike: 218, bid: 1.86, ask: 1.89, iv: 0.29, delta: -0.50, volume: 380 }
    }
  });

  const [isConnected, setIsConnected] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const wsRef = useRef(null);

  useEffect(() => {
    // Initialize WebSocket connection for real-time data
    const connectWebSocket = () => {
      try {
        wsRef.current = new WebSocket('ws://localhost:8000/api/v1/market-data/stream');
        
        wsRef.current.onopen = () => {
          setIsConnected(true);
          console.log('Market data WebSocket connected');
        };

        wsRef.current.onmessage = (event) => {
          const message = JSON.parse(event.data);
          handleWebSocketMessage(message);
          setLastUpdate(new Date());
        };

        wsRef.current.onclose = () => {
          setIsConnected(false);
          console.log('Market data WebSocket disconnected');
          // Reconnect after 5 seconds
          setTimeout(connectWebSocket, 5000);
        };

        wsRef.current.onerror = (error) => {
          console.error('WebSocket error:', error);
          setIsConnected(false);
        };
      } catch (error) {
        console.error('Failed to connect WebSocket:', error);
        setIsConnected(false);
      }
    };

    connectWebSocket();

    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleWebSocketMessage = (message) => {
    switch (message.type) {
      case 'market_data':
        const { symbol, price, volume, bid, ask } = message.data;
        setMarketData(prev => ({
          ...prev,
          [symbol]: {
            ...prev[symbol],
            price,
            volume,
            bid,
            ask
          }
        }));
        break;
      
      case 'vix_data':
        setVixData(message.data);
        break;
      
      case 'correlation_data':
        setCorrelationData(message.data);
        break;
      
      default:
        console.log('Unknown message type:', message.type);
    }
  };

  const formatPrice = (price) => price.toFixed(2);
  const formatChange = (change) => change >= 0 ? `+${change.toFixed(2)}` : change.toFixed(2);
  const formatPercent = (percent) => percent >= 0 ? `+${percent.toFixed(2)}%` : `${percent.toFixed(2)}%`;
  const formatVolume = (volume) => {
    if (volume >= 1000000) return `${(volume / 1000000).toFixed(1)}M`;
    if (volume >= 1000) return `${(volume / 1000).toFixed(0)}K`;
    return volume.toString();
  };

  const getVixRegimeColor = (regime) => {
    switch (regime) {
      case 'low': return 'bg-green-100 text-green-800';
      case 'normal': return 'bg-blue-100 text-blue-800';
      case 'elevated': return 'bg-yellow-100 text-yellow-800';
      case 'high': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getCorrelationColor = (correlation) => {
    const abs = Math.abs(correlation);
    if (abs >= 0.8) return 'text-red-600';
    if (abs >= 0.6) return 'text-yellow-600';
    return 'text-green-600';
  };

  const refreshData = async () => {
    try {
      // Simulate data refresh
      setLastUpdate(new Date());
      // In real implementation, this would fetch fresh data from API
    } catch (error) {
      console.error('Error refreshing data:', error);
    }
  };

  const exportData = async (symbol, format = 'csv') => {
    try {
      const response = await fetch(`/api/v1/market-data/export/${symbol}?format=${format}`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${symbol}_data.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error exporting data:', error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with Status */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Market Data Dashboard</h2>
          <p className="text-muted-foreground">
            Real-time ETF & VIX data for focused 0DTE trading
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            {isConnected ? (
              <CheckCircle className="h-4 w-4 text-green-500" />
            ) : (
              <AlertTriangle className="h-4 w-4 text-red-500" />
            )}
            <span className="text-sm text-muted-foreground">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <div className="text-sm text-muted-foreground">
            Last update: {lastUpdate.toLocaleTimeString()}
          </div>
          <Button onClick={refreshData} size="sm" variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="options">Options</TabsTrigger>
          <TabsTrigger value="vix">VIX Analysis</TabsTrigger>
          <TabsTrigger value="correlations">Correlations</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            {Object.entries(marketData).map(([symbol, data]) => (
              <Card key={symbol}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">{symbol}</CardTitle>
                  <div className="flex items-center space-x-2">
                    {data.changePercent >= 0 ? (
                      <TrendingUp className="h-4 w-4 text-green-600" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-red-600" />
                    )}
                    <Button
                      onClick={() => exportData(symbol)}
                      size="sm"
                      variant="ghost"
                    >
                      <Download className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">${formatPrice(data.price)}</div>
                  <div className={`text-xs ${data.changePercent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatChange(data.change)} ({formatPercent(data.changePercent)})
                  </div>
                  <div className="mt-4 space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Volume:</span>
                      <span>{formatVolume(data.volume)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Bid/Ask:</span>
                      <span>${formatPrice(data.bid)} / ${formatPrice(data.ask)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Spread:</span>
                      <span>${formatPrice(data.ask - data.bid)}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* VIX Overview Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Activity className="h-5 w-5" />
                <span>VIX Volatility Index</span>
                <Badge className={getVixRegimeColor(vixData.regime)}>
                  {vixData.regime.toUpperCase()} VOLATILITY
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-4">
                <div>
                  <div className="text-2xl font-bold">{vixData.level}</div>
                  <div className={`text-xs ${vixData.changePercent >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {formatChange(vixData.change)} ({formatPercent(vixData.changePercent)})
                  </div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">VIX9D</div>
                  <div className="text-lg font-semibold">{vixData.termStructure.VIX9D}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">VIX3M</div>
                  <div className="text-lg font-semibold">{vixData.termStructure.VIX3M}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">VIX6M</div>
                  <div className="text-lg font-semibold">{vixData.termStructure.VIX6M}</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Options Tab */}
        <TabsContent value="options" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            {Object.entries(optionsData).map(([symbol, data]) => (
              <Card key={symbol}>
                <CardHeader>
                  <CardTitle>{symbol} ATM Options</CardTitle>
                  <CardDescription>At-the-money call and put options</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Call Option */}
                  <div className="p-3 border rounded-lg bg-green-50">
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-medium text-green-700">CALL ${data.atmCall.strike}</span>
                      <Badge variant="outline" className="text-green-700">
                        Vol: {data.atmCall.volume}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-muted-foreground">Bid/Ask:</span>
                        <div>${data.atmCall.bid} / ${data.atmCall.ask}</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">IV:</span>
                        <div>{(data.atmCall.iv * 100).toFixed(1)}%</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Delta:</span>
                        <div>{data.atmCall.delta.toFixed(3)}</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Spread:</span>
                        <div>${(data.atmCall.ask - data.atmCall.bid).toFixed(2)}</div>
                      </div>
                    </div>
                  </div>

                  {/* Put Option */}
                  <div className="p-3 border rounded-lg bg-red-50">
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-medium text-red-700">PUT ${data.atmPut.strike}</span>
                      <Badge variant="outline" className="text-red-700">
                        Vol: {data.atmPut.volume}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-muted-foreground">Bid/Ask:</span>
                        <div>${data.atmPut.bid} / ${data.atmPut.ask}</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">IV:</span>
                        <div>{(data.atmPut.iv * 100).toFixed(1)}%</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Delta:</span>
                        <div>{data.atmPut.delta.toFixed(3)}</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Spread:</span>
                        <div>${(data.atmPut.ask - data.atmPut.bid).toFixed(2)}</div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* VIX Analysis Tab */}
        <TabsContent value="vix" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>VIX Term Structure</CardTitle>
                <CardDescription>Volatility across different time horizons</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {Object.entries(vixData.termStructure).map(([term, value]) => (
                    <div key={term} className="flex items-center space-x-4">
                      <div className="w-16 text-sm font-medium">{term}</div>
                      <div className="flex-1">
                        <Progress value={(value / 30) * 100} className="h-2" />
                      </div>
                      <div className="w-12 text-sm font-semibold">{value}</div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Volatility Regime Analysis</CardTitle>
                <CardDescription>Current market volatility environment</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span>Current Regime:</span>
                    <Badge className={getVixRegimeColor(vixData.regime)}>
                      {vixData.regime.toUpperCase()}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>VIX Level:</span>
                    <span className="font-semibold">{vixData.level}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Daily Change:</span>
                    <span className={vixData.changePercent >= 0 ? 'text-red-600' : 'text-green-600'}>
                      {formatPercent(vixData.changePercent)}
                    </span>
                  </div>
                  <Separator />
                  <div className="text-sm text-muted-foreground">
                    <p>
                      <strong>Low Volatility (VIX &lt; 15):</strong> Favorable for selling premium
                    </p>
                    <p>
                      <strong>Normal Volatility (15-20):</strong> Balanced market conditions
                    </p>
                    <p>
                      <strong>Elevated Volatility (20-30):</strong> Increased risk, higher premiums
                    </p>
                    <p>
                      <strong>High Volatility (VIX &gt; 30):</strong> Crisis mode, extreme caution
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Correlations Tab */}
        <TabsContent value="correlations" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>ETF Correlations</CardTitle>
                <CardDescription>Inter-ETF correlation matrix</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span>SPY ↔ QQQ:</span>
                    <span className={`font-semibold ${getCorrelationColor(correlationData.spyQqq)}`}>
                      {correlationData.spyQqq.toFixed(3)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>SPY ↔ IWM:</span>
                    <span className={`font-semibold ${getCorrelationColor(correlationData.spyIwm)}`}>
                      {correlationData.spyIwm.toFixed(3)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>QQQ ↔ IWM:</span>
                    <span className={`font-semibold ${getCorrelationColor(correlationData.qqIwm)}`}>
                      {correlationData.qqIwm.toFixed(3)}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>VIX Correlations</CardTitle>
                <CardDescription>ETF correlation with volatility index</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span>SPY ↔ VIX:</span>
                    <span className={`font-semibold ${getCorrelationColor(correlationData.spyVix)}`}>
                      {correlationData.spyVix.toFixed(3)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>QQQ ↔ VIX:</span>
                    <span className={`font-semibold ${getCorrelationColor(correlationData.qqVix)}`}>
                      {correlationData.qqVix.toFixed(3)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>IWM ↔ VIX:</span>
                    <span className={`font-semibold ${getCorrelationColor(correlationData.iwmVix)}`}>
                      {correlationData.iwmVix.toFixed(3)}
                    </span>
                  </div>
                  <Separator />
                  <div className="flex items-center justify-between">
                    <span>Regime Change Probability:</span>
                    <Badge variant={correlationData.regimeChangeProbability > 0.5 ? 'destructive' : 'secondary'}>
                      {(correlationData.regimeChangeProbability * 100).toFixed(1)}%
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Market Performance</CardTitle>
                <CardDescription>Daily performance metrics</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {Object.entries(marketData).map(([symbol, data]) => (
                    <div key={symbol} className="flex items-center justify-between">
                      <span className="font-medium">{symbol}</span>
                      <div className="text-right">
                        <div className={`font-semibold ${data.changePercent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatPercent(data.changePercent)}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          Vol: {formatVolume(data.volume)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Trading Opportunities</CardTitle>
                <CardDescription>AI-identified opportunities</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="p-3 border rounded-lg bg-blue-50">
                    <div className="flex items-center space-x-2 mb-2">
                      <Target className="h-4 w-4 text-blue-600" />
                      <span className="font-medium text-blue-700">Mean Reversion Signal</span>
                    </div>
                    <p className="text-sm text-blue-600">
                      SPY showing oversold conditions with VIX regime support
                    </p>
                  </div>
                  
                  <div className="p-3 border rounded-lg bg-yellow-50">
                    <div className="flex items-center space-x-2 mb-2">
                      <Zap className="h-4 w-4 text-yellow-600" />
                      <span className="font-medium text-yellow-700">Volatility Play</span>
                    </div>
                    <p className="text-sm text-yellow-600">
                      Low VIX environment favors premium selling strategies
                    </p>
                  </div>
                  
                  <div className="p-3 border rounded-lg bg-green-50">
                    <div className="flex items-center space-x-2 mb-2">
                      <BarChart3 className="h-4 w-4 text-green-600" />
                      <span className="font-medium text-green-700">Correlation Breakdown</span>
                    </div>
                    <p className="text-sm text-green-600">
                      QQQ-IWM correlation weakening, pairs trade opportunity
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default MarketDataDashboard;

