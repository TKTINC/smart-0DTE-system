import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Button } from './components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Progress } from './components/ui/progress';
import { Separator } from './components/ui/separator';
import { ScrollArea } from './components/ui/scroll-area';
import ConversationalAI from './components/ConversationalAI';
import AdvancedReporting from './components/AdvancedReporting';
import MarketDataDashboard from './components/MarketDataDashboard';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  AreaChart, Area, BarChart, Bar, ScatterChart, Scatter, Cell
} from 'recharts'
import { 
  TrendingUp, TrendingDown, Activity, DollarSign, Target, Shield, 
  Brain, Zap, AlertTriangle, CheckCircle, Clock, Settings,
  BarChart3, PieChart, Gauge, Eye, Play, Pause, Square, MessageCircle
} from 'lucide-react'
import './App.css'

// Mock data for demonstration
const mockMarketData = {
  SPY: { price: 485.67, change: 2.34, changePercent: 0.48, volume: 45678900 },
  QQQ: { price: 412.89, change: -1.23, changePercent: -0.30, volume: 32145600 },
  IWM: { price: 218.45, change: 0.87, changePercent: 0.40, volume: 18923400 }
}

const mockVixData = {
  level: 16.8,
  change: -0.45,
  regime: 'Low Volatility',
  percentile: 25
}

const mockSignals = [
  {
    id: 'signal_1',
    symbol: 'SPY',
    type: 'Correlation Breakdown',
    strength: 'STRONG',
    confidence: 0.85,
    timestamp: '2024-12-07 14:23:15',
    reasoning: ['SPY-QQQ correlation dropped to 0.65', 'Divergence detected in momentum']
  },
  {
    id: 'signal_2',
    symbol: 'QQQ',
    type: 'AI Prediction',
    strength: 'MEDIUM',
    confidence: 0.72,
    timestamp: '2024-12-07 14:18:42',
    reasoning: ['Technical indicators suggest reversal', 'Volume profile supports move']
  }
]

const mockPerformanceData = [
  { date: '2024-12-01', value: 50000, spy: 49800 },
  { date: '2024-12-02', value: 50234, spy: 49950 },
  { date: '2024-12-03', value: 49876, spy: 49700 },
  { date: '2024-12-04', value: 50456, spy: 50100 },
  { date: '2024-12-05', value: 50123, spy: 49850 },
  { date: '2024-12-06', value: 50789, spy: 50200 },
  { date: '2024-12-07', value: 50567, spy: 50050 }
]

function App() {
  const [activeTab, setActiveTab] = useState('overview')
  const [isTrading, setIsTrading] = useState(false)
  const [currentTime, setCurrentTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value)
  }

  const formatPercentage = (value) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  const getChangeColor = (value) => {
    return value >= 0 ? 'text-green-600' : 'text-red-600'
  }

  const getBadgeVariant = (value) => {
    return value >= 0 ? 'default' : 'destructive'
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <h1 className="text-2xl font-bold text-gray-900">Smart-0DTE-System</h1>
                <p className="text-sm text-gray-500">Advanced Options Trading Platform</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-500">
                {currentTime.toLocaleTimeString()}
              </div>
              <Badge variant={isTrading ? 'default' : 'secondary'}>
                {isTrading ? 'Trading Active' : 'Market Closed'}
              </Badge>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-7">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="signals">Signals</TabsTrigger>
          <TabsTrigger value="strategies">Strategies</TabsTrigger>
          <TabsTrigger value="options">Options</TabsTrigger>
          <TabsTrigger value="market-data">Market Data</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          <TabsTrigger value="ai-assistant">AI Assistant</TabsTrigger>
        </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            {/* Market Overview */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {Object.entries(mockMarketData).map(([symbol, data]) => (
                <Card key={symbol}>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-600">{symbol}</p>
                        <p className="text-2xl font-bold">{formatCurrency(data.price)}</p>
                      </div>
                      <div className="text-right">
                        <p className={`text-sm font-medium ${getChangeColor(data.change)}`}>
                          {formatCurrency(data.change)}
                        </p>
                        <Badge variant={getBadgeVariant(data.change)}>
                          {formatPercentage(data.changePercent)}
                        </Badge>
                      </div>
                    </div>
                    <div className="mt-2">
                      <p className="text-xs text-gray-500">Vol: {(data.volume / 1000000).toFixed(1)}M</p>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* VIX and Performance */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>VIX Analysis</CardTitle>
                  <CardDescription>Volatility regime and market sentiment</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Current Level</span>
                      <span className="text-2xl font-bold">{mockVixData.level}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Change</span>
                      <span className={`font-medium ${getChangeColor(mockVixData.change)}`}>
                        {mockVixData.change}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Regime</span>
                      <Badge variant="secondary">{mockVixData.regime}</Badge>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Percentile</span>
                        <span>{mockVixData.percentile}%</span>
                      </div>
                      <Progress value={mockVixData.percentile} className="h-2" />
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Today's Performance</CardTitle>
                  <CardDescription>Portfolio vs SPY benchmark</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={mockPerformanceData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" hide />
                      <YAxis hide />
                      <Tooltip 
                        formatter={(value) => formatCurrency(value)}
                        labelFormatter={(label) => `Date: ${label}`}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="value" 
                        stroke="#3b82f6" 
                        strokeWidth={2}
                        name="Portfolio"
                      />
                      <Line 
                        type="monotone" 
                        dataKey="spy" 
                        stroke="#94a3b8" 
                        strokeWidth={1}
                        strokeDasharray="5 5"
                        name="SPY"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                  <div className="mt-4 grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-600">Portfolio</p>
                      <p className="text-lg font-bold text-blue-600">+$567.89</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">vs SPY</p>
                      <p className="text-lg font-bold text-green-600">+0.23%</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Recent Signals */}
            <Card>
              <CardHeader>
                <CardTitle>Recent AI Signals</CardTitle>
                <CardDescription>Latest trading opportunities identified</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {mockSignals.map((signal) => (
                    <div key={signal.id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center space-x-4">
                        <Badge variant="outline">{signal.symbol}</Badge>
                        <div>
                          <p className="font-medium">{signal.type}</p>
                          <p className="text-sm text-gray-600">{signal.timestamp}</p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Badge variant={signal.strength === 'STRONG' ? 'default' : 'secondary'}>
                          {Math.round(signal.confidence * 100)}%
                        </Badge>
                        <Button size="sm" variant="outline">View</Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Signals Tab */}
          <TabsContent value="signals" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>AI Signal Generation</CardTitle>
                <CardDescription>Real-time market analysis and trading opportunities</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600">Advanced signal analysis interface coming soon...</p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Strategies Tab */}
          <TabsContent value="strategies" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Trading Strategies</CardTitle>
                <CardDescription>Strategy performance and configuration</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600">Strategy management interface coming soon...</p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Options Tab */}
          <TabsContent value="options" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Options Chain</CardTitle>
                <CardDescription>Real-time options data and analysis</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600">Options chain interface coming soon...</p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Market Data Tab */}
          <TabsContent value="market-data" className="space-y-4">
            <MarketDataDashboard />
          </TabsContent>

          {/* Analytics Tab */}
          <TabsContent value="analytics" className="space-y-4">
            <AdvancedReporting />
          </TabsContent>

          {/* AI Assistant Tab */}
          <TabsContent value="ai-assistant" className="space-y-4">
            <ConversationalAI />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}

export default App

