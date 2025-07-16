import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Button } from './components/ui/button';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Progress } from './components/ui/progress';
import ConversationalAI from './components/ConversationalAI';
import AdvancedReporting from './components/AdvancedReporting';/slider'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import ConversationalAI from '@/components/ConversationalAI'
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
    strength: 'MODERATE',
    confidence: 0.72,
    timestamp: '2024-12-07 14:18:42',
    reasoning: ['AI model confidence: 72%', 'Volatility expansion predicted']
  }
]

const mockStrategies = [
  {
    id: 'strategy_1',
    symbol: 'SPY',
    type: 'Iron Condor',
    status: 'Active',
    pnl: 45.67,
    maxProfit: 120.00,
    maxLoss: 380.00,
    confidence: 0.85
  },
  {
    id: 'strategy_2',
    symbol: 'QQQ',
    type: 'Bull Call Spread',
    status: 'Active',
    pnl: -23.45,
    maxProfit: 200.00,
    maxLoss: 300.00,
    confidence: 0.72
  }
]

const mockChartData = [
  { time: '09:30', SPY: 483.45, QQQ: 414.23, IWM: 217.89, VIX: 17.2 },
  { time: '10:00', SPY: 484.12, QQQ: 413.67, IWM: 218.12, VIX: 16.9 },
  { time: '10:30', SPY: 485.23, QQQ: 412.89, IWM: 218.45, VIX: 16.8 },
  { time: '11:00', SPY: 485.67, QQQ: 412.34, IWM: 218.67, VIX: 16.5 },
  { time: '11:30', SPY: 485.89, QQQ: 412.89, IWM: 218.23, VIX: 16.8 }
]

const mockCorrelationData = [
  { pair: 'SPY-QQQ', correlation: 0.65, change: -0.15, status: 'breakdown' },
  { pair: 'SPY-IWM', correlation: 0.78, change: 0.02, status: 'normal' },
  { pair: 'QQQ-IWM', correlation: 0.72, change: -0.08, status: 'weakening' }
]

function App() {
  const [isSystemActive, setIsSystemActive] = useState(true)
  const [confidenceThreshold, setConfidenceThreshold] = useState([65])
  const [selectedSymbol, setSelectedSymbol] = useState('SPY')
  const [currentTime, setCurrentTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    })
  }

  const getChangeColor = (change) => {
    return change >= 0 ? 'text-green-600' : 'text-red-600'
  }

  const getSignalStrengthColor = (strength) => {
    switch (strength) {
      case 'STRONG': return 'bg-green-500'
      case 'MODERATE': return 'bg-yellow-500'
      case 'WEAK': return 'bg-orange-500'
      default: return 'bg-gray-500'
    }
  }

  const getStrategyStatusColor = (status) => {
    switch (status) {
      case 'Active': return 'bg-blue-500'
      case 'Closed': return 'bg-gray-500'
      case 'Pending': return 'bg-yellow-500'
      default: return 'bg-gray-500'
    }
  }

  return (
    <div className="min-h-screen bg-background p-4 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Brain className="h-8 w-8 text-primary" />
            <h1 className="text-3xl font-bold">Smart-0DTE-System</h1>
          </div>
          <Badge variant={isSystemActive ? "default" : "secondary"} className="text-sm">
            {isSystemActive ? "ACTIVE" : "PAUSED"}
          </Badge>
        </div>
        
        <div className="flex items-center space-x-4">
          <div className="text-right">
            <div className="text-sm text-muted-foreground">Market Time</div>
            <div className="text-lg font-mono">{formatTime(currentTime)}</div>
          </div>
          <div className="flex items-center space-x-2">
            <Switch 
              checked={isSystemActive} 
              onCheckedChange={setIsSystemActive}
            />
            <span className="text-sm">System Active</span>
          </div>
        </div>
      </div>

      {/* System Status Alert */}
      {!isSystemActive && (
        <Alert className="border-yellow-500 bg-yellow-50 dark:bg-yellow-950">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>System Paused</AlertTitle>
          <AlertDescription>
            Trading automation is currently paused. No new signals will be executed.
          </AlertDescription>
        </Alert>
      )}

      {/* Market Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {Object.entries(mockMarketData).map(([symbol, data]) => (
          <Card key={symbol} className="cursor-pointer hover:shadow-lg transition-shadow">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">{symbol}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="text-2xl font-bold">${data.price}</div>
                <div className={`flex items-center space-x-1 ${getChangeColor(data.change)}`}>
                  {data.change >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                  <span>{data.change >= 0 ? '+' : ''}{data.change}</span>
                  <span>({data.changePercent >= 0 ? '+' : ''}{data.changePercent}%)</span>
                </div>
                <div className="text-sm text-muted-foreground">
                  Vol: {(data.volume / 1000000).toFixed(1)}M
                </div>
              </div>
            </CardContent>
          </Card>
        ))}

        {/* VIX Card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center space-x-2">
              <Gauge className="h-5 w-5" />
              <span>VIX</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="text-2xl font-bold">{mockVixData.level}</div>
              <div className={`flex items-center space-x-1 ${getChangeColor(mockVixData.change)}`}>
                {mockVixData.change >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                <span>{mockVixData.change}</span>
              </div>
              <div className="text-sm">
                <Badge variant="outline">{mockVixData.regime}</Badge>
              </div>
              <Progress value={mockVixData.percentile} className="h-2" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Dashboard */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="grid w-full grid-cols-7">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="signals">Signals</TabsTrigger>
          <TabsTrigger value="strategies">Strategies</TabsTrigger>
          <TabsTrigger value="options">Options</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          <TabsTrigger value="ai-assistant">
            <MessageCircle className="h-4 w-4 mr-1" />
            AI Assistant
          </TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Price Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <BarChart3 className="h-5 w-5" />
                  <span>Real-time Price Action</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={mockChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="SPY" stroke="#8884d8" strokeWidth={2} />
                    <Line type="monotone" dataKey="QQQ" stroke="#82ca9d" strokeWidth={2} />
                    <Line type="monotone" dataKey="IWM" stroke="#ffc658" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Correlation Matrix */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Activity className="h-5 w-5" />
                  <span>Cross-Ticker Correlations</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {mockCorrelationData.map((item, index) => (
                    <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center space-x-3">
                        <span className="font-medium">{item.pair}</span>
                        <Badge variant={item.status === 'breakdown' ? 'destructive' : 'outline'}>
                          {item.status}
                        </Badge>
                      </div>
                      <div className="text-right">
                        <div className="font-bold">{item.correlation.toFixed(3)}</div>
                        <div className={`text-sm ${getChangeColor(item.change)}`}>
                          {item.change >= 0 ? '+' : ''}{item.change.toFixed(3)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* VIX Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Gauge className="h-5 w-5" />
                <span>VIX & Market Regime</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={mockChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Area type="monotone" dataKey="VIX" stroke="#ff7300" fill="#ff7300" fillOpacity={0.3} />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Signals Tab */}
        <TabsContent value="signals" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold">Active Signals</h2>
            <div className="flex items-center space-x-4">
              <span className="text-sm">Confidence Threshold: {confidenceThreshold[0]}%</span>
              <Slider
                value={confidenceThreshold}
                onValueChange={setConfidenceThreshold}
                max={100}
                min={50}
                step={5}
                className="w-32"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {mockSignals.map((signal) => (
              <Card key={signal.id} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center space-x-2">
                      <Zap className="h-5 w-5" />
                      <span>{signal.symbol} - {signal.type}</span>
                    </CardTitle>
                    <Badge className={getSignalStrengthColor(signal.strength)}>
                      {signal.strength}
                    </Badge>
                  </div>
                  <CardDescription>
                    Confidence: {(signal.confidence * 100).toFixed(0)}% • {signal.timestamp}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <Progress value={signal.confidence * 100} className="h-2" />
                    <div className="space-y-1">
                      {signal.reasoning.map((reason, index) => (
                        <div key={index} className="text-sm text-muted-foreground flex items-center space-x-2">
                          <CheckCircle className="h-3 w-3" />
                          <span>{reason}</span>
                        </div>
                      ))}
                    </div>
                    <div className="flex space-x-2 pt-2">
                      <Button size="sm" className="flex-1">
                        <Play className="h-4 w-4 mr-1" />
                        Execute
                      </Button>
                      <Button size="sm" variant="outline" className="flex-1">
                        <Eye className="h-4 w-4 mr-1" />
                        Analyze
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Strategies Tab */}
        <TabsContent value="strategies" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold">Active Strategies</h2>
            <Button>
              <Target className="h-4 w-4 mr-2" />
              New Strategy
            </Button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {mockStrategies.map((strategy) => (
              <Card key={strategy.id} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center space-x-2">
                      <Target className="h-5 w-5" />
                      <span>{strategy.symbol} - {strategy.type}</span>
                    </CardTitle>
                    <Badge className={getStrategyStatusColor(strategy.status)}>
                      {strategy.status}
                    </Badge>
                  </div>
                  <CardDescription>
                    Confidence: {(strategy.confidence * 100).toFixed(0)}%
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div>
                        <div className="text-sm text-muted-foreground">Current P&L</div>
                        <div className={`text-lg font-bold ${getChangeColor(strategy.pnl)}`}>
                          ${strategy.pnl.toFixed(2)}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Max Profit</div>
                        <div className="text-lg font-bold text-green-600">
                          ${strategy.maxProfit.toFixed(2)}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Max Loss</div>
                        <div className="text-lg font-bold text-red-600">
                          ${strategy.maxLoss.toFixed(2)}
                        </div>
                      </div>
                    </div>
                    
                    <Progress 
                      value={((strategy.pnl + strategy.maxLoss) / (strategy.maxProfit + strategy.maxLoss)) * 100} 
                      className="h-2" 
                    />
                    
                    <div className="flex space-x-2">
                      <Button size="sm" variant="outline" className="flex-1">
                        <Eye className="h-4 w-4 mr-1" />
                        Details
                      </Button>
                      <Button size="sm" variant="destructive" className="flex-1">
                        <Square className="h-4 w-4 mr-1" />
                        Close
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Options Tab */}
        <TabsContent value="options" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold">0DTE Options Chain</h2>
            <div className="flex items-center space-x-2">
              <span className="text-sm">Symbol:</span>
              <select 
                value={selectedSymbol} 
                onChange={(e) => setSelectedSymbol(e.target.value)}
                className="px-3 py-1 border rounded"
              >
                <option value="SPY">SPY</option>
                <option value="QQQ">QQQ</option>
                <option value="IWM">IWM</option>
              </select>
            </div>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>{selectedSymbol} Options Chain - Expiring Today</CardTitle>
              <CardDescription>
                Underlying: ${mockMarketData[selectedSymbol].price} • ATM ±10 Strikes
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center text-muted-foreground py-8">
                <PieChart className="h-12 w-12 mx-auto mb-4" />
                <p>Options chain data would be displayed here</p>
                <p className="text-sm">Real-time Greeks, IV, and volume analysis</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics" className="space-y-4">
          <h2 className="text-2xl font-bold">Performance Analytics</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <DollarSign className="h-5 w-5" />
                  <span>Today's P&L</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-green-600">+$234.56</div>
                <div className="text-sm text-muted-foreground">+2.34% return</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Target className="h-5 w-5" />
                  <span>Win Rate</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">68.5%</div>
                <div className="text-sm text-muted-foreground">23 of 34 trades</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Brain className="h-5 w-5" />
                  <span>AI Accuracy</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">74.2%</div>
                <div className="text-sm text-muted-foreground">Signal prediction</div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Performance Chart</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center text-muted-foreground py-8">
                <BarChart3 className="h-12 w-12 mx-auto mb-4" />
                <p>Performance analytics would be displayed here</p>
                <p className="text-sm">P&L curves, drawdown analysis, and risk metrics</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* AI Assistant Tab */}
        <TabsContent value="ai-assistant" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
              <ConversationalAI 
                tradingData={{
                  marketData: mockMarketData,
                  vixData: mockVixData,
                  signals: mockSignals,
                  strategies: mockStrategies,
                  correlations: mockCorrelationData
                }}
                onFeedback={(messageId, isPositive) => {
                  console.log(`Feedback for message ${messageId}: ${isPositive ? 'positive' : 'negative'}`)
                  // Here you would typically send feedback to your backend for learning
                }}
              />
            </div>
            
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Brain className="h-5 w-5" />
                    <span>AI Insights</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="p-3 bg-blue-50 rounded-lg">
                      <div className="font-medium text-sm">Market Regime</div>
                      <div className="text-xs text-muted-foreground">Low volatility environment detected</div>
                    </div>
                    <div className="p-3 bg-yellow-50 rounded-lg">
                      <div className="font-medium text-sm">Correlation Alert</div>
                      <div className="text-xs text-muted-foreground">SPY-QQQ correlation breakdown</div>
                    </div>
                    <div className="p-3 bg-green-50 rounded-lg">
                      <div className="font-medium text-sm">Strategy Recommendation</div>
                      <div className="text-xs text-muted-foreground">Mean reversion strategies favored</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Target className="h-5 w-5" />
                    <span>Quick Actions</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <Button variant="outline" size="sm" className="w-full justify-start">
                      Analyze yesterday's performance
                    </Button>
                    <Button variant="outline" size="sm" className="w-full justify-start">
                      Explain current signals
                    </Button>
                    <Button variant="outline" size="sm" className="w-full justify-start">
                      Risk assessment
                    </Button>
                    <Button variant="outline" size="sm" className="w-full justify-start">
                      Strategy optimization
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings" className="space-y-4">
          <h2 className="text-2xl font-bold">System Settings</h2>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Settings className="h-5 w-5" />
                  <span>Trading Parameters</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span>Auto-execute signals</span>
                  <Switch defaultChecked />
                </div>
                <div className="flex items-center justify-between">
                  <span>Emergency halt enabled</span>
                  <Switch defaultChecked />
                </div>
                <div className="space-y-2">
                  <span>Max positions per symbol: 3</span>
                  <Slider defaultValue={[3]} max={10} min={1} step={1} />
                </div>
                <div className="space-y-2">
                  <span>Profit target: 10%</span>
                  <Slider defaultValue={[10]} max={50} min={5} step={5} />
                </div>
                <div className="space-y-2">
                  <span>Stop loss: 10%</span>
                  <Slider defaultValue={[10]} max={50} min={5} step={5} />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Shield className="h-5 w-5" />
                  <span>Risk Management</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span>VIX-based position sizing</span>
                  <Switch defaultChecked />
                </div>
                <div className="flex items-center justify-between">
                  <span>Correlation monitoring</span>
                  <Switch defaultChecked />
                </div>
                <div className="space-y-2">
                  <span>Max daily loss: $1000</span>
                  <Slider defaultValue={[1000]} max={5000} min={100} step={100} />
                </div>
                <div className="space-y-2">
                  <span>VIX emergency threshold: 30</span>
                  <Slider defaultValue={[30]} max={50} min={20} step={1} />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default App

