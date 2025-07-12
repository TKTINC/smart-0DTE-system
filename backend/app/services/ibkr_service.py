"""
Smart-0DTE-System IBKR Integration Service

This module provides comprehensive Interactive Brokers integration for
automated options trading with real-time execution and monitoring.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from enum import Enum
import threading
import time

from ib_insync import IB, Stock, Option, Contract, Order, Trade, Position, AccountValue
from ib_insync import MarketOrder, LimitOrder, StopOrder, BracketOrder
from ib_insync import util

from app.core.config import settings
from app.core.redis_client import market_data_cache
from app.models.trading_models import IBKRAccount, IBKROrder, IBKRPosition
from app.services.trading_strategy_service import trading_strategy_service

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PARTIAL = "partial"


class IBKRService:
    """
    Interactive Brokers Integration Service
    
    Provides automated trading capabilities including order execution,
    position monitoring, and account management for 0DTE options strategies.
    """
    
    def __init__(self):
        self.ib = IB()
        self.is_connected = False
        self.is_running = False
        
        # Connection parameters
        self.connection_config = {
            'host': settings.IBKR_HOST,
            'port': settings.IBKR_PORT,
            'client_id': settings.IBKR_CLIENT_ID,
            'timeout': 30
        }
        
        # Trading parameters
        self.trading_config = {
            'max_orders_per_minute': 10,
            'order_timeout_seconds': 30,
            'position_check_interval': 10,
            'account_update_interval': 60
        }
        
        # State tracking
        self.active_orders = {}
        self.active_positions = {}
        self.account_info = {}
        self.order_history = []
        
        # Rate limiting
        self.order_timestamps = []
        
        # Event handlers
        self.ib.orderStatusEvent += self._on_order_status
        self.ib.execDetailsEvent += self._on_execution
        self.ib.positionEvent += self._on_position_update
        self.ib.accountValueEvent += self._on_account_update
        self.ib.errorEvent += self._on_error
    
    async def initialize(self) -> None:
        """Initialize IBKR service."""
        try:
            # Connect to IBKR
            await self._connect_to_ibkr()
            
            # Initialize account data
            await self._initialize_account_data()
            
            logger.info("IBKR Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize IBKR Service: {e}")
            raise
    
    async def start_trading_automation(self) -> None:
        """Start automated trading processes."""
        try:
            if not self.is_connected:
                await self._connect_to_ibkr()
            
            self.is_running = True
            
            # Start background tasks
            asyncio.create_task(self._monitor_strategy_signals())
            asyncio.create_task(self._monitor_positions())
            asyncio.create_task(self._update_account_info())
            asyncio.create_task(self._manage_orders())
            
            logger.info("IBKR trading automation started")
            
        except Exception as e:
            logger.error(f"Failed to start trading automation: {e}")
            raise
    
    async def stop_trading_automation(self) -> None:
        """Stop automated trading processes."""
        try:
            self.is_running = False
            
            # Cancel all pending orders
            await self._cancel_all_orders()
            
            # Disconnect from IBKR
            if self.is_connected:
                self.ib.disconnect()
                self.is_connected = False
            
            logger.info("IBKR trading automation stopped")
            
        except Exception as e:
            logger.error(f"Error stopping trading automation: {e}")
    
    async def _connect_to_ibkr(self) -> None:
        """Connect to Interactive Brokers."""
        try:
            # Connect to IBKR Gateway/TWS
            self.ib.connect(
                host=self.connection_config['host'],
                port=self.connection_config['port'],
                clientId=self.connection_config['client_id'],
                timeout=self.connection_config['timeout']
            )
            
            self.is_connected = True
            
            # Request account updates
            self.ib.reqAccountUpdates(True, '')
            
            logger.info(f"Connected to IBKR at {self.connection_config['host']}:{self.connection_config['port']}")
            
        except Exception as e:
            logger.error(f"Failed to connect to IBKR: {e}")
            self.is_connected = False
            raise
    
    async def _initialize_account_data(self) -> None:
        """Initialize account data and positions."""
        try:
            if not self.is_connected:
                return
            
            # Get account summary
            account_summary = self.ib.accountSummary()
            
            # Get current positions
            positions = self.ib.positions()
            
            # Get open orders
            open_orders = self.ib.openOrders()
            
            # Process account data
            for item in account_summary:
                self.account_info[item.tag] = {
                    'value': item.value,
                    'currency': item.currency,
                    'account': item.account
                }
            
            # Process positions
            for position in positions:
                position_key = f"{position.contract.symbol}_{position.contract.secType}"
                self.active_positions[position_key] = {
                    'contract': position.contract,
                    'position': position.position,
                    'avg_cost': position.avgCost,
                    'market_price': position.marketPrice,
                    'market_value': position.marketValue,
                    'unrealized_pnl': position.unrealizedPNL
                }
            
            # Process open orders
            for order in open_orders:
                self.active_orders[order.orderId] = {
                    'order': order,
                    'status': 'submitted',
                    'timestamp': datetime.utcnow()
                }
            
            logger.info("Account data initialized")
            
        except Exception as e:
            logger.error(f"Error initializing account data: {e}")
    
    async def _monitor_strategy_signals(self) -> None:
        """Monitor trading strategy signals and execute trades."""
        while self.is_running:
            try:
                # Get active signals from trading strategy service
                signals = await trading_strategy_service.get_active_signals()
                
                for signal in signals:
                    # Check if signal should be executed
                    should_execute = await self._should_execute_signal(signal)
                    
                    if should_execute:
                        # Execute signal
                        execution_result = await self._execute_signal(signal)
                        
                        if execution_result.get('success'):
                            logger.info(f"Successfully executed signal: {signal['id']}")
                        else:
                            logger.warning(f"Failed to execute signal: {signal['id']}")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring strategy signals: {e}")
                await asyncio.sleep(5)
    
    async def _should_execute_signal(self, signal: Dict[str, Any]) -> bool:
        """Determine if a signal should be executed."""
        try:
            # Check if already executed
            signal_id = signal.get('id', '')
            if signal_id in [order.get('signal_id') for order in self.active_orders.values()]:
                return False
            
            # Check rate limiting
            if not self._check_rate_limit():
                return False
            
            # Check account requirements
            if not await self._check_account_requirements(signal):
                return False
            
            # Check market hours
            if not self._is_market_open():
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking signal execution: {e}")
            return False
    
    def _check_rate_limit(self) -> bool:
        """Check if order rate limit is exceeded."""
        try:
            current_time = time.time()
            
            # Remove old timestamps (older than 1 minute)
            self.order_timestamps = [
                ts for ts in self.order_timestamps
                if current_time - ts < 60
            ]
            
            # Check if under limit
            return len(self.order_timestamps) < self.trading_config['max_orders_per_minute']
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return False
    
    async def _check_account_requirements(self, signal: Dict[str, Any]) -> bool:
        """Check if account meets requirements for signal execution."""
        try:
            # Get buying power
            buying_power = float(self.account_info.get('BuyingPower', {}).get('value', 0))
            
            # Estimate required capital (simplified)
            estimated_cost = 1000  # $1000 per strategy (would be calculated based on actual strategy)
            
            if buying_power < estimated_cost:
                logger.warning(f"Insufficient buying power: {buying_power} < {estimated_cost}")
                return False
            
            # Check position limits
            symbol = signal.get('symbol', '')
            symbol_positions = len([
                pos for pos in self.active_positions.values()
                if pos['contract'].symbol == symbol
            ])
            
            if symbol_positions >= 3:  # Max 3 positions per symbol
                logger.warning(f"Position limit reached for {symbol}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking account requirements: {e}")
            return False
    
    def _is_market_open(self) -> bool:
        """Check if market is currently open."""
        try:
            current_time = datetime.now()
            current_hour = current_time.hour
            current_minute = current_time.minute
            weekday = current_time.weekday()
            
            # Market closed on weekends
            if weekday >= 5:  # Saturday = 5, Sunday = 6
                return False
            
            # Market hours: 9:30 AM - 4:00 PM ET
            market_open_time = 9 * 60 + 30  # 9:30 AM in minutes
            market_close_time = 16 * 60     # 4:00 PM in minutes
            current_time_minutes = current_hour * 60 + current_minute
            
            return market_open_time <= current_time_minutes <= market_close_time
            
        except Exception as e:
            logger.error(f"Error checking market hours: {e}")
            return True  # Default to open for development
    
    async def _execute_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a trading signal."""
        try:
            # Get strategy for signal
            strategies = await trading_strategy_service.get_active_strategies()
            strategy = None
            
            for s in strategies:
                if s.get('signal_id') == signal.get('id'):
                    strategy = s
                    break
            
            if not strategy:
                return {'success': False, 'error': 'No strategy found for signal'}
            
            # Execute strategy
            execution_result = await self._execute_strategy(strategy)
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _execute_strategy(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an options strategy."""
        try:
            strategy_type = strategy.get('strategy_type', '')
            legs = strategy.get('legs', [])
            
            if not legs:
                return {'success': False, 'error': 'No legs in strategy'}
            
            # Create orders for each leg
            orders = []
            
            for leg in legs:
                order = await self._create_option_order(leg, strategy)
                if order:
                    orders.append(order)
            
            if not orders:
                return {'success': False, 'error': 'Failed to create orders'}
            
            # Submit orders
            submitted_orders = []
            
            for order_data in orders:
                submitted_order = await self._submit_order(order_data['contract'], order_data['order'])
                if submitted_order:
                    submitted_orders.append(submitted_order)
                    
                    # Track order
                    self.active_orders[submitted_order.orderId] = {
                        'order': submitted_order,
                        'contract': order_data['contract'],
                        'strategy_id': strategy.get('id'),
                        'signal_id': strategy.get('signal_id'),
                        'status': 'submitted',
                        'timestamp': datetime.utcnow()
                    }
            
            # Update rate limiting
            self.order_timestamps.append(time.time())
            
            return {
                'success': True,
                'strategy_id': strategy.get('id'),
                'orders': [order.orderId for order in submitted_orders],
                'execution_time': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error executing strategy: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _create_option_order(self, leg: Dict[str, Any], strategy: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create an option order for a strategy leg."""
        try:
            symbol = strategy.get('symbol', '')
            expiration = strategy.get('expiration', '')
            
            # Create option contract
            contract = Option(
                symbol=symbol,
                lastTradeDateOrContractMonth=expiration.replace('-', ''),
                strike=leg.get('strike', 0),
                right=leg.get('option_type', 'C').upper(),
                exchange='SMART',
                currency='USD'
            )
            
            # Qualify contract
            qualified_contracts = self.ib.qualifyContracts(contract)
            if not qualified_contracts:
                logger.error(f"Failed to qualify contract: {contract}")
                return None
            
            contract = qualified_contracts[0]
            
            # Create order
            action = 'BUY' if leg.get('action') == 'buy' else 'SELL'
            quantity = leg.get('quantity', 1)
            
            # Use limit order with premium from leg
            limit_price = leg.get('premium', 0)
            
            order = LimitOrder(
                action=action,
                totalQuantity=quantity,
                lmtPrice=limit_price,
                tif='DAY'  # Day order
            )
            
            return {
                'contract': contract,
                'order': order
            }
            
        except Exception as e:
            logger.error(f"Error creating option order: {e}")
            return None
    
    async def _submit_order(self, contract: Contract, order: Order) -> Optional[Trade]:
        """Submit an order to IBKR."""
        try:
            if not self.is_connected:
                logger.error("Not connected to IBKR")
                return None
            
            # Place order
            trade = self.ib.placeOrder(contract, order)
            
            # Wait for order to be submitted
            await asyncio.sleep(1)
            
            return trade
            
        except Exception as e:
            logger.error(f"Error submitting order: {e}")
            return None
    
    async def _monitor_positions(self) -> None:
        """Monitor active positions for P&L and exit conditions."""
        while self.is_running:
            try:
                # Update positions
                positions = self.ib.positions()
                
                for position in positions:
                    if position.position == 0:
                        continue
                    
                    position_key = f"{position.contract.symbol}_{position.contract.secType}"
                    
                    # Update position data
                    self.active_positions[position_key] = {
                        'contract': position.contract,
                        'position': position.position,
                        'avg_cost': position.avgCost,
                        'market_price': position.marketPrice,
                        'market_value': position.marketValue,
                        'unrealized_pnl': position.unrealizedPNL
                    }
                    
                    # Check exit conditions
                    await self._check_position_exit_conditions(position)
                
                await asyncio.sleep(self.trading_config['position_check_interval'])
                
            except Exception as e:
                logger.error(f"Error monitoring positions: {e}")
                await asyncio.sleep(5)
    
    async def _check_position_exit_conditions(self, position) -> None:
        """Check if position should be closed based on exit conditions."""
        try:
            # Get strategy for this position
            strategy = await self._get_strategy_for_position(position)
            
            if not strategy:
                return
            
            # Check profit target
            profit_target = strategy.get('profit_target', 0)
            if position.unrealizedPNL >= profit_target:
                await self._close_position(position, 'profit_target')
                return
            
            # Check stop loss
            stop_loss = strategy.get('stop_loss', 0)
            if position.unrealizedPNL <= -stop_loss:
                await self._close_position(position, 'stop_loss')
                return
            
            # Check time-based exit (close before market close for 0DTE)
            current_time = datetime.now()
            if current_time.hour >= 15 and current_time.minute >= 45:  # 3:45 PM
                await self._close_position(position, 'time_exit')
                return
            
        except Exception as e:
            logger.error(f"Error checking position exit conditions: {e}")
    
    async def _get_strategy_for_position(self, position) -> Optional[Dict[str, Any]]:
        """Get strategy associated with a position."""
        try:
            # This would match positions to strategies based on contracts
            # For now, return None (would be implemented with proper position tracking)
            return None
            
        except Exception as e:
            logger.error(f"Error getting strategy for position: {e}")
            return None
    
    async def _close_position(self, position, reason: str) -> None:
        """Close a position."""
        try:
            # Create closing order
            action = 'SELL' if position.position > 0 else 'BUY'
            quantity = abs(position.position)
            
            # Use market order for quick exit
            order = MarketOrder(
                action=action,
                totalQuantity=quantity
            )
            
            # Submit closing order
            trade = await self._submit_order(position.contract, order)
            
            if trade:
                logger.info(f"Closing position for {position.contract.symbol} - Reason: {reason}")
                
                # Track closing order
                self.active_orders[trade.orderId] = {
                    'order': trade,
                    'contract': position.contract,
                    'status': 'submitted',
                    'close_reason': reason,
                    'timestamp': datetime.utcnow()
                }
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
    
    async def _update_account_info(self) -> None:
        """Update account information periodically."""
        while self.is_running:
            try:
                if not self.is_connected:
                    await asyncio.sleep(10)
                    continue
                
                # Get account summary
                account_summary = self.ib.accountSummary()
                
                # Update account info
                for item in account_summary:
                    self.account_info[item.tag] = {
                        'value': item.value,
                        'currency': item.currency,
                        'account': item.account
                    }
                
                # Cache account info
                await market_data_cache.redis.set(
                    'ibkr_account_info',
                    self.account_info,
                    ttl=300
                )
                
                await asyncio.sleep(self.trading_config['account_update_interval'])
                
            except Exception as e:
                logger.error(f"Error updating account info: {e}")
                await asyncio.sleep(10)
    
    async def _manage_orders(self) -> None:
        """Manage active orders and handle timeouts."""
        while self.is_running:
            try:
                current_time = datetime.utcnow()
                timeout_threshold = timedelta(seconds=self.trading_config['order_timeout_seconds'])
                
                # Check for timed out orders
                timed_out_orders = []
                
                for order_id, order_data in self.active_orders.items():
                    order_time = order_data.get('timestamp', current_time)
                    
                    if current_time - order_time > timeout_threshold:
                        if order_data.get('status') == 'submitted':
                            timed_out_orders.append(order_id)
                
                # Cancel timed out orders
                for order_id in timed_out_orders:
                    await self._cancel_order(order_id)
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error managing orders: {e}")
                await asyncio.sleep(5)
    
    async def _cancel_order(self, order_id: int) -> bool:
        """Cancel a specific order."""
        try:
            if order_id not in self.active_orders:
                return False
            
            order_data = self.active_orders[order_id]
            trade = order_data.get('order')
            
            if trade:
                self.ib.cancelOrder(trade.order)
                order_data['status'] = 'cancelled'
                logger.info(f"Cancelled order: {order_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def _cancel_all_orders(self) -> None:
        """Cancel all active orders."""
        try:
            for order_id in list(self.active_orders.keys()):
                await self._cancel_order(order_id)
            
            logger.info("All orders cancelled")
            
        except Exception as e:
            logger.error(f"Error cancelling all orders: {e}")
    
    # Event handlers
    
    def _on_order_status(self, trade: Trade) -> None:
        """Handle order status updates."""
        try:
            order_id = trade.order.orderId
            
            if order_id in self.active_orders:
                self.active_orders[order_id]['status'] = trade.orderStatus.status.lower()
                
                logger.info(f"Order {order_id} status: {trade.orderStatus.status}")
                
                # If filled, update position tracking
                if trade.orderStatus.status == 'Filled':
                    self._handle_order_fill(trade)
            
        except Exception as e:
            logger.error(f"Error handling order status: {e}")
    
    def _on_execution(self, trade: Trade, fill) -> None:
        """Handle order executions."""
        try:
            order_id = trade.order.orderId
            
            logger.info(f"Order {order_id} executed: {fill.execution.shares} @ {fill.execution.price}")
            
            # Update order history
            self.order_history.append({
                'order_id': order_id,
                'execution_time': datetime.utcnow(),
                'shares': fill.execution.shares,
                'price': fill.execution.price,
                'commission': fill.commissionReport.commission if fill.commissionReport else 0
            })
            
        except Exception as e:
            logger.error(f"Error handling execution: {e}")
    
    def _on_position_update(self, position) -> None:
        """Handle position updates."""
        try:
            position_key = f"{position.contract.symbol}_{position.contract.secType}"
            
            if position.position == 0:
                # Position closed
                if position_key in self.active_positions:
                    del self.active_positions[position_key]
                    logger.info(f"Position closed: {position_key}")
            else:
                # Position updated
                self.active_positions[position_key] = {
                    'contract': position.contract,
                    'position': position.position,
                    'avg_cost': position.avgCost,
                    'market_price': position.marketPrice,
                    'market_value': position.marketValue,
                    'unrealized_pnl': position.unrealizedPNL
                }
            
        except Exception as e:
            logger.error(f"Error handling position update: {e}")
    
    def _on_account_update(self, account_value: AccountValue) -> None:
        """Handle account value updates."""
        try:
            self.account_info[account_value.tag] = {
                'value': account_value.value,
                'currency': account_value.currency,
                'account': account_value.account
            }
            
        except Exception as e:
            logger.error(f"Error handling account update: {e}")
    
    def _on_error(self, reqId: int, errorCode: int, errorString: str, contract) -> None:
        """Handle IBKR errors."""
        try:
            logger.error(f"IBKR Error {errorCode}: {errorString} (reqId: {reqId})")
            
            # Handle specific error codes
            if errorCode in [502, 504]:  # Connection errors
                self.is_connected = False
                logger.warning("IBKR connection lost")
            
        except Exception as e:
            logger.error(f"Error handling IBKR error: {e}")
    
    def _handle_order_fill(self, trade: Trade) -> None:
        """Handle order fill events."""
        try:
            order_id = trade.order.orderId
            
            # Update order status
            if order_id in self.active_orders:
                self.active_orders[order_id]['status'] = 'filled'
                self.active_orders[order_id]['fill_time'] = datetime.utcnow()
            
            logger.info(f"Order {order_id} filled successfully")
            
        except Exception as e:
            logger.error(f"Error handling order fill: {e}")
    
    # Public API methods
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get current account information."""
        try:
            return self.account_info.copy()
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}
    
    async def get_active_positions(self) -> Dict[str, Any]:
        """Get current active positions."""
        try:
            return self.active_positions.copy()
        except Exception as e:
            logger.error(f"Error getting active positions: {e}")
            return {}
    
    async def get_active_orders(self) -> Dict[str, Any]:
        """Get current active orders."""
        try:
            return self.active_orders.copy()
        except Exception as e:
            logger.error(f"Error getting active orders: {e}")
            return {}
    
    async def get_order_history(self) -> List[Dict[str, Any]]:
        """Get order execution history."""
        try:
            return self.order_history.copy()
        except Exception as e:
            logger.error(f"Error getting order history: {e}")
            return []
    
    async def manual_order(self, contract_details: Dict[str, Any], order_details: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a manual order."""
        try:
            # Create contract
            if contract_details.get('secType') == 'OPT':
                contract = Option(
                    symbol=contract_details.get('symbol'),
                    lastTradeDateOrContractMonth=contract_details.get('expiration'),
                    strike=contract_details.get('strike'),
                    right=contract_details.get('right'),
                    exchange='SMART',
                    currency='USD'
                )
            else:
                contract = Stock(
                    symbol=contract_details.get('symbol'),
                    exchange='SMART',
                    currency='USD'
                )
            
            # Qualify contract
            qualified_contracts = self.ib.qualifyContracts(contract)
            if not qualified_contracts:
                return {'success': False, 'error': 'Failed to qualify contract'}
            
            contract = qualified_contracts[0]
            
            # Create order
            order_type = order_details.get('type', 'LMT')
            
            if order_type == 'MKT':
                order = MarketOrder(
                    action=order_details.get('action'),
                    totalQuantity=order_details.get('quantity')
                )
            else:
                order = LimitOrder(
                    action=order_details.get('action'),
                    totalQuantity=order_details.get('quantity'),
                    lmtPrice=order_details.get('price')
                )
            
            # Submit order
            trade = await self._submit_order(contract, order)
            
            if trade:
                return {
                    'success': True,
                    'order_id': trade.orderId,
                    'status': 'submitted'
                }
            else:
                return {'success': False, 'error': 'Failed to submit order'}
            
        except Exception as e:
            logger.error(f"Error submitting manual order: {e}")
            return {'success': False, 'error': str(e)}
    
    async def health_check(self) -> bool:
        """Check IBKR service health."""
        try:
            if not self.is_connected:
                return False
            
            # Check if we can get account info
            if not self.account_info:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"IBKR Service health check failed: {e}")
            return False


# Global IBKR service instance
ibkr_service = IBKRService()

