import React, { useState, useEffect, useRef } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  MessageCircle, Send, Bot, User, TrendingDown, TrendingUp, 
  AlertTriangle, CheckCircle, Brain, Clock, BarChart3, Target,
  ThumbsUp, ThumbsDown, RefreshCw, Lightbulb
} from 'lucide-react'

// Mock trading history and context data
const mockTradingHistory = {
  yesterday: {
    date: '2024-12-06',
    totalPnL: -156.78,
    trades: [
      {
        symbol: 'SPY',
        strategy: 'Iron Condor',
        entry: '09:45',
        exit: '15:30',
        pnl: -89.45,
        reason: 'Unexpected volatility spike broke upper wing',
        confidence: 0.82
      },
      {
        symbol: 'QQQ',
        strategy: 'Bull Call Spread',
        entry: '10:15',
        exit: '14:20',
        pnl: -67.33,
        reason: 'Tech selloff exceeded stop loss',
        confidence: 0.75
      }
    ],
    marketConditions: {
      vixSpike: 3.2,
      correlationBreakdown: true,
      unexpectedNews: 'Fed hawkish comments at 2PM'
    }
  },
  lastWeek: {
    totalPnL: 234.56,
    winRate: 0.68,
    bestStrategy: 'Mean Reversion',
    worstStrategy: 'Momentum Breakout'
  }
}

const ConversationalAI = ({ tradingData, onFeedback }) => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'ai',
      content: "Hi! I'm your AI trading assistant. I can analyze your performance, explain what happened on specific days, and help you understand your trading patterns. Try asking me something like 'What went wrong yesterday?' or 'Why did my SPY trade fail?'",
      timestamp: new Date(),
      confidence: 0.95
    }
  ])
  const [inputMessage, setInputMessage] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Contextual AI response generator
  const generateAIResponse = async (userQuery) => {
    setIsAnalyzing(true)
    
    // Simulate AI processing time
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    const query = userQuery.toLowerCase()
    let response = { content: '', confidence: 0.8, insights: [], recommendations: [] }

    // Pattern matching for different types of queries
    if (query.includes('yesterday') || query.includes('what went wrong')) {
      response = analyzeYesterdayPerformance(query)
    } else if (query.includes('spy') && (query.includes('fail') || query.includes('loss'))) {
      response = analyzeSPYTrade(query)
    } else if (query.includes('strategy') || query.includes('performance')) {
      response = analyzeStrategyPerformance(query)
    } else if (query.includes('market') || query.includes('volatility')) {
      response = analyzeMarketConditions(query)
    } else if (query.includes('improve') || query.includes('better')) {
      response = provideImprovementSuggestions(query)
    } else {
      response = {
        content: "I can help you analyze your trading performance and explain what happened. Try asking about specific days, strategies, or symbols. For example: 'What went wrong yesterday?', 'Why did my SPY trade fail?', or 'How can I improve my performance?'",
        confidence: 0.9,
        insights: [],
        recommendations: []
      }
    }

    setIsAnalyzing(false)
    return response
  }

  const analyzeYesterdayPerformance = (query) => {
    const yesterday = mockTradingHistory.yesterday
    return {
      content: `Yesterday (${yesterday.date}) was challenging with a total loss of $${Math.abs(yesterday.totalPnL).toFixed(2)}. Here's what happened:

**Main Issues:**
1. **SPY Iron Condor (-$${Math.abs(yesterday.trades[0].pnl).toFixed(2)})**: An unexpected volatility spike at 2PM broke through the upper wing. The VIX jumped ${yesterday.marketConditions.vixSpike} points due to hawkish Fed comments.

2. **QQQ Bull Call Spread (-$${Math.abs(yesterday.trades[1].pnl).toFixed(2)})**: Tech sector selloff exceeded our stop loss levels. The correlation breakdown between SPY-QQQ (dropped to 0.65) wasn't anticipated.

**Root Cause**: The Fed's unexpected hawkish tone at 2PM caused a volatility regime shift that our models didn't predict. Both trades were positioned for low volatility continuation.`,
      confidence: 0.92,
      insights: [
        'Volatility regime change was the primary factor',
        'Correlation breakdown between major ETFs',
        'News-driven market move outside normal patterns'
      ],
      recommendations: [
        'Consider wider wings on condors during Fed weeks',
        'Implement news-aware position sizing',
        'Add VIX hedging for low-vol strategies'
      ]
    }
  }

  const analyzeSPYTrade = (query) => {
    const spyTrade = mockTradingHistory.yesterday.trades[0]
    return {
      content: `Your SPY Iron Condor failed due to an unexpected volatility expansion. Here's the detailed breakdown:

**Trade Details:**
- Entry: ${spyTrade.entry} with ${(spyTrade.confidence * 100).toFixed(0)}% confidence
- Strategy: ${spyTrade.strategy}
- Loss: $${Math.abs(spyTrade.pnl).toFixed(2)}

**What Went Wrong:**
The upper wing was breached when SPY moved beyond our expected range. The Fed's hawkish comments at 2PM caused a ${mockTradingHistory.yesterday.marketConditions.vixSpike}-point VIX spike, expanding realized volatility beyond our model's predictions.

**Technical Analysis:**
- Expected range: $480-$490
- Actual high: $492.45 (breach at 2:15PM)
- IV expansion: 15% above morning levels`,
      confidence: 0.88,
      insights: [
        'Fed communication risk not properly hedged',
        'Upper wing too narrow for event risk',
        'Volatility model underestimated tail risk'
      ],
      recommendations: [
        'Use wider strikes during Fed weeks',
        'Consider calendar spreads instead of condors',
        'Add gamma hedging for large positions'
      ]
    }
  }

  const analyzeStrategyPerformance = (query) => {
    return {
      content: `Here's your strategy performance analysis:

**Last Week Performance:**
- **Best Strategy**: Mean Reversion (${mockTradingHistory.lastWeek.bestStrategy}) - Consistent profits in range-bound markets
- **Worst Strategy**: Momentum Breakout - Failed in choppy conditions
- **Overall Win Rate**: ${(mockTradingHistory.lastWeek.winRate * 100).toFixed(1)}%
- **Net P&L**: +$${mockTradingHistory.lastWeek.totalPnL.toFixed(2)}

**Strategy Insights:**
Mean reversion worked well because the market stayed range-bound most of the week. Momentum strategies struggled due to false breakouts and quick reversals.`,
      confidence: 0.85,
      insights: [
        'Range-bound market favored mean reversion',
        'False breakouts hurt momentum strategies',
        'Correlation patterns were more stable'
      ],
      recommendations: [
        'Increase allocation to mean reversion in low-vol regimes',
        'Add breakout confirmation filters',
        'Consider hybrid strategies for uncertain markets'
      ]
    }
  }

  const analyzeMarketConditions = (query) => {
    return {
      content: `Current market analysis:

**Volatility Regime**: Low (VIX: 16.8)
**Correlation Status**: SPY-QQQ correlation breakdown detected (0.65 vs normal 0.85)
**Market Sentiment**: Mixed with tech underperforming

**Key Factors:**
- VIX in 25th percentile (low volatility)
- Sector rotation from tech to value
- Fed policy uncertainty creating intermittent spikes

This environment favors range-bound strategies but requires careful position sizing due to potential volatility expansion.`,
      confidence: 0.90,
      insights: [
        'Low volatility environment with spike risk',
        'Sector rotation affecting correlations',
        'Fed policy creating uncertainty'
      ],
      recommendations: [
        'Focus on range-bound strategies',
        'Maintain VIX hedging',
        'Monitor correlation changes closely'
      ]
    }
  }

  const provideImprovementSuggestions = (query) => {
    return {
      content: `Based on your recent performance, here are key improvement areas:

**Risk Management:**
1. **Position Sizing**: Consider reducing size during Fed weeks by 25-30%
2. **Volatility Hedging**: Add VIX calls for low-vol strategies
3. **Stop Losses**: Implement dynamic stops based on realized volatility

**Strategy Optimization:**
1. **Market Regime Awareness**: Adjust strategy mix based on VIX percentile
2. **Correlation Monitoring**: Add correlation breakdown alerts
3. **News Integration**: Factor in scheduled economic events

**Performance Enhancement:**
- Your mean reversion strategies are working well - consider increasing allocation
- Momentum strategies need refinement for current market conditions`,
      confidence: 0.87,
      insights: [
        'Risk management needs enhancement',
        'Strategy allocation could be optimized',
        'Market regime awareness is crucial'
      ],
      recommendations: [
        'Implement dynamic position sizing',
        'Add volatility hedging protocols',
        'Enhance news-aware trading rules'
      ]
    }
  }

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return

    const userMessage = {
      id: messages.length + 1,
      type: 'user',
      content: inputMessage,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsTyping(true)

    try {
      const aiResponse = await generateAIResponse(inputMessage)
      
      const aiMessage = {
        id: messages.length + 2,
        type: 'ai',
        content: aiResponse.content,
        timestamp: new Date(),
        confidence: aiResponse.confidence,
        insights: aiResponse.insights,
        recommendations: aiResponse.recommendations
      }

      setMessages(prev => [...prev, aiMessage])
    } catch (error) {
      const errorMessage = {
        id: messages.length + 2,
        type: 'ai',
        content: "I'm having trouble analyzing that right now. Please try again or rephrase your question.",
        timestamp: new Date(),
        confidence: 0.5,
        isError: true
      }
      setMessages(prev => [...prev, errorMessage])
    }

    setIsTyping(false)
  }

  const handleFeedback = (messageId, isPositive) => {
    setMessages(prev => prev.map(msg => 
      msg.id === messageId 
        ? { ...msg, feedback: isPositive ? 'positive' : 'negative' }
        : msg
    ))
    
    if (onFeedback) {
      onFeedback(messageId, isPositive)
    }
  }

  const formatTimestamp = (timestamp) => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <Card className="h-[600px] flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2">
          <Brain className="h-5 w-5 text-blue-500" />
          AI Trading Assistant
          <Badge variant="outline" className="ml-auto">
            <Bot className="h-3 w-3 mr-1" />
            Online
          </Badge>
        </CardTitle>
        <CardDescription>
          Ask me about your trading performance, strategies, or market analysis
        </CardDescription>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0">
        <ScrollArea className="flex-1 px-4">
          <div className="space-y-4 pb-4">
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] ${message.type === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-100'} rounded-lg p-3`}>
                  <div className="flex items-start gap-2">
                    {message.type === 'ai' && <Bot className="h-4 w-4 mt-1 text-blue-500" />}
                    {message.type === 'user' && <User className="h-4 w-4 mt-1" />}
                    <div className="flex-1">
                      <div className="whitespace-pre-wrap text-sm">
                        {message.content}
                      </div>
                      
                      {message.insights && message.insights.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <div className="flex items-center gap-1 mb-2">
                            <Lightbulb className="h-3 w-3 text-yellow-500" />
                            <span className="text-xs font-medium text-gray-600">Key Insights</span>
                          </div>
                          <ul className="text-xs text-gray-600 space-y-1">
                            {message.insights.map((insight, idx) => (
                              <li key={idx} className="flex items-start gap-1">
                                <span className="text-yellow-500">•</span>
                                {insight}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {message.recommendations && message.recommendations.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <div className="flex items-center gap-1 mb-2">
                            <Target className="h-3 w-3 text-green-500" />
                            <span className="text-xs font-medium text-gray-600">Recommendations</span>
                          </div>
                          <ul className="text-xs text-gray-600 space-y-1">
                            {message.recommendations.map((rec, idx) => (
                              <li key={idx} className="flex items-start gap-1">
                                <span className="text-green-500">•</span>
                                {rec}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      <div className="flex items-center justify-between mt-2">
                        <span className="text-xs text-gray-500">
                          {formatTimestamp(message.timestamp)}
                          {message.confidence && (
                            <span className="ml-2">
                              Confidence: {(message.confidence * 100).toFixed(0)}%
                            </span>
                          )}
                        </span>
                        
                        {message.type === 'ai' && !message.isError && (
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 w-6 p-0"
                              onClick={() => handleFeedback(message.id, true)}
                            >
                              <ThumbsUp className={`h-3 w-3 ${message.feedback === 'positive' ? 'text-green-500' : 'text-gray-400'}`} />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 w-6 p-0"
                              onClick={() => handleFeedback(message.id, false)}
                            >
                              <ThumbsDown className={`h-3 w-3 ${message.feedback === 'negative' ? 'text-red-500' : 'text-gray-400'}`} />
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            
            {isTyping && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-lg p-3 max-w-[80%]">
                  <div className="flex items-center gap-2">
                    <Bot className="h-4 w-4 text-blue-500" />
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                    {isAnalyzing && (
                      <span className="text-xs text-gray-500 ml-2">Analyzing trading data...</span>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
          <div ref={messagesEndRef} />
        </ScrollArea>

        <Separator />
        
        <div className="p-4">
          <div className="flex gap-2">
            <Input
              placeholder="Ask me about your trading performance..."
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              disabled={isTyping}
            />
            <Button 
              onClick={handleSendMessage} 
              disabled={isTyping || !inputMessage.trim()}
              size="sm"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
          
          <div className="flex flex-wrap gap-2 mt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setInputMessage("What went wrong yesterday?")}
              disabled={isTyping}
            >
              What went wrong yesterday?
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setInputMessage("Why did my SPY trade fail?")}
              disabled={isTyping}
            >
              Why did my SPY trade fail?
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setInputMessage("How can I improve my performance?")}
              disabled={isTyping}
            >
              How can I improve?
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default ConversationalAI

