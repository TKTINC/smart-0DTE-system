"""
Tax Service for Smart-0DTE-System

This service handles all tax-related calculations including:
- Wash sale rule detection and adjustments
- Short-term vs long-term capital gains classification
- Tax optimization recommendations
- Tax-efficient trading strategies
- Performance reporting with tax implications
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class TaxLotMethod(Enum):
    """Tax lot identification methods."""
    FIFO = "fifo"  # First In, First Out
    LIFO = "lifo"  # Last In, First Out
    SPECIFIC = "specific"  # Specific identification
    AVERAGE = "average"  # Average cost


class GainType(Enum):
    """Capital gain types for tax purposes."""
    SHORT_TERM = "short_term"  # Held <= 1 year
    LONG_TERM = "long_term"    # Held > 1 year


@dataclass
class TaxLot:
    """Represents a tax lot for position tracking."""
    symbol: str
    quantity: int
    cost_basis: float
    acquisition_date: datetime
    lot_id: str
    is_wash_sale: bool = False
    wash_sale_adjustment: float = 0.0


@dataclass
class TaxableEvent:
    """Represents a taxable trading event."""
    symbol: str
    trade_date: datetime
    quantity: int
    price: float
    trade_type: str  # 'buy' or 'sell'
    proceeds: float
    cost_basis: float
    gain_loss: float
    gain_type: GainType
    is_wash_sale: bool = False
    wash_sale_adjustment: float = 0.0
    tax_lot_ids: List[str] = None


@dataclass
class TaxSummary:
    """Tax summary for a given period."""
    period_start: datetime
    period_end: datetime
    short_term_gains: float
    long_term_gains: float
    total_gains: float
    wash_sale_adjustments: float
    realized_gains: float
    unrealized_gains: float
    tax_efficiency_score: float
    recommendations: List[str]


class TaxService:
    """Service for handling tax calculations and optimization."""
    
    def __init__(self):
        self.tax_lots: Dict[str, List[TaxLot]] = {}  # symbol -> list of tax lots
        self.taxable_events: List[TaxableEvent] = []
        self.wash_sale_period = 30  # days
        self.tax_lot_method = TaxLotMethod.FIFO
        
    async def process_trade(
        self,
        symbol: str,
        trade_date: datetime,
        quantity: int,
        price: float,
        trade_type: str
    ) -> Optional[TaxableEvent]:
        """
        Process a trade and calculate tax implications.
        
        Args:
            symbol: Trading symbol (SPY, QQQ, IWM, VIX)
            trade_date: Date of the trade
            quantity: Number of shares/contracts
            price: Price per share/contract
            trade_type: 'buy' or 'sell'
            
        Returns:
            TaxableEvent if it's a sale, None for purchases
        """
        try:
            if trade_type.lower() == 'buy':
                return await self._process_purchase(symbol, trade_date, quantity, price)
            elif trade_type.lower() == 'sell':
                return await self._process_sale(symbol, trade_date, quantity, price)
            else:
                logger.error(f"Invalid trade type: {trade_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing trade: {e}")
            return None
    
    async def _process_purchase(
        self,
        symbol: str,
        trade_date: datetime,
        quantity: int,
        price: float
    ) -> None:
        """Process a purchase transaction."""
        lot_id = f"{symbol}_{trade_date.isoformat()}_{quantity}_{price}"
        cost_basis = quantity * price
        
        tax_lot = TaxLot(
            symbol=symbol,
            quantity=quantity,
            cost_basis=cost_basis,
            acquisition_date=trade_date,
            lot_id=lot_id
        )
        
        if symbol not in self.tax_lots:
            self.tax_lots[symbol] = []
        
        self.tax_lots[symbol].append(tax_lot)
        logger.info(f"Added tax lot: {lot_id}")
        
        return None
    
    async def _process_sale(
        self,
        symbol: str,
        trade_date: datetime,
        quantity: int,
        price: float
    ) -> TaxableEvent:
        """Process a sale transaction and calculate gains/losses."""
        if symbol not in self.tax_lots or not self.tax_lots[symbol]:
            logger.warning(f"No tax lots available for {symbol}")
            return None
        
        proceeds = quantity * price
        lots_to_sell = await self._select_tax_lots(symbol, quantity)
        
        total_cost_basis = 0.0
        used_lot_ids = []
        
        for lot, lot_quantity in lots_to_sell:
            lot_cost_basis = (lot.cost_basis / lot.quantity) * lot_quantity
            total_cost_basis += lot_cost_basis
            used_lot_ids.append(lot.lot_id)
            
            # Update or remove the tax lot
            lot.quantity -= lot_quantity
            if lot.quantity <= 0:
                self.tax_lots[symbol].remove(lot)
        
        gain_loss = proceeds - total_cost_basis
        
        # Determine gain type (short-term vs long-term)
        gain_type = await self._determine_gain_type(lots_to_sell, trade_date)
        
        # Check for wash sale
        is_wash_sale, wash_adjustment = await self._check_wash_sale(
            symbol, trade_date, gain_loss
        )
        
        taxable_event = TaxableEvent(
            symbol=symbol,
            trade_date=trade_date,
            quantity=quantity,
            price=price,
            trade_type='sell',
            proceeds=proceeds,
            cost_basis=total_cost_basis,
            gain_loss=gain_loss,
            gain_type=gain_type,
            is_wash_sale=is_wash_sale,
            wash_sale_adjustment=wash_adjustment,
            tax_lot_ids=used_lot_ids
        )
        
        self.taxable_events.append(taxable_event)
        logger.info(f"Processed sale: {symbol} - Gain/Loss: ${gain_loss:.2f}")
        
        return taxable_event
    
    async def _select_tax_lots(
        self,
        symbol: str,
        quantity: int
    ) -> List[Tuple[TaxLot, int]]:
        """Select tax lots based on the configured method."""
        available_lots = [lot for lot in self.tax_lots[symbol] if lot.quantity > 0]
        
        if self.tax_lot_method == TaxLotMethod.FIFO:
            available_lots.sort(key=lambda x: x.acquisition_date)
        elif self.tax_lot_method == TaxLotMethod.LIFO:
            available_lots.sort(key=lambda x: x.acquisition_date, reverse=True)
        
        lots_to_sell = []
        remaining_quantity = quantity
        
        for lot in available_lots:
            if remaining_quantity <= 0:
                break
                
            lot_quantity = min(lot.quantity, remaining_quantity)
            lots_to_sell.append((lot, lot_quantity))
            remaining_quantity -= lot_quantity
        
        if remaining_quantity > 0:
            logger.warning(f"Insufficient shares for {symbol}: need {quantity}, have {quantity - remaining_quantity}")
        
        return lots_to_sell
    
    async def _determine_gain_type(
        self,
        lots_to_sell: List[Tuple[TaxLot, int]],
        sale_date: datetime
    ) -> GainType:
        """Determine if gains are short-term or long-term."""
        # For simplicity, use the oldest lot's holding period
        if not lots_to_sell:
            return GainType.SHORT_TERM
        
        oldest_lot = min(lots_to_sell, key=lambda x: x[0].acquisition_date)[0]
        holding_period = sale_date - oldest_lot.acquisition_date
        
        return GainType.LONG_TERM if holding_period.days > 365 else GainType.SHORT_TERM
    
    async def _check_wash_sale(
        self,
        symbol: str,
        sale_date: datetime,
        gain_loss: float
    ) -> Tuple[bool, float]:
        """Check for wash sale rule violations."""
        if gain_loss >= 0:  # Wash sale only applies to losses
            return False, 0.0
        
        # Check for purchases within 30 days before or after the sale
        wash_start = sale_date - timedelta(days=self.wash_sale_period)
        wash_end = sale_date + timedelta(days=self.wash_sale_period)
        
        # Check recent purchases
        if symbol in self.tax_lots:
            for lot in self.tax_lots[symbol]:
                if wash_start <= lot.acquisition_date <= wash_end:
                    # Wash sale detected
                    return True, abs(gain_loss)
        
        # Check future purchases (would need to be implemented with trade scheduling)
        # For now, we'll just check historical data
        
        return False, 0.0
    
    async def generate_tax_summary(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> TaxSummary:
        """Generate a comprehensive tax summary for the period."""
        period_events = [
            event for event in self.taxable_events
            if start_date <= event.trade_date <= end_date
        ]
        
        short_term_gains = sum(
            event.gain_loss for event in period_events
            if event.gain_type == GainType.SHORT_TERM and not event.is_wash_sale
        )
        
        long_term_gains = sum(
            event.gain_loss for event in period_events
            if event.gain_type == GainType.LONG_TERM and not event.is_wash_sale
        )
        
        wash_sale_adjustments = sum(
            event.wash_sale_adjustment for event in period_events
            if event.is_wash_sale
        )
        
        total_gains = short_term_gains + long_term_gains
        realized_gains = total_gains - wash_sale_adjustments
        
        # Calculate unrealized gains (current positions)
        unrealized_gains = await self._calculate_unrealized_gains()
        
        # Calculate tax efficiency score
        tax_efficiency_score = await self._calculate_tax_efficiency(
            short_term_gains, long_term_gains, wash_sale_adjustments
        )
        
        # Generate recommendations
        recommendations = await self._generate_tax_recommendations(
            short_term_gains, long_term_gains, wash_sale_adjustments
        )
        
        return TaxSummary(
            period_start=start_date,
            period_end=end_date,
            short_term_gains=short_term_gains,
            long_term_gains=long_term_gains,
            total_gains=total_gains,
            wash_sale_adjustments=wash_sale_adjustments,
            realized_gains=realized_gains,
            unrealized_gains=unrealized_gains,
            tax_efficiency_score=tax_efficiency_score,
            recommendations=recommendations
        )
    
    async def _calculate_unrealized_gains(self) -> float:
        """Calculate unrealized gains for current positions."""
        # This would typically fetch current market prices
        # For now, return a placeholder
        return 0.0
    
    async def _calculate_tax_efficiency(
        self,
        short_term_gains: float,
        long_term_gains: float,
        wash_sale_adjustments: float
    ) -> float:
        """Calculate a tax efficiency score (0-100)."""
        total_gains = short_term_gains + long_term_gains
        
        if total_gains == 0:
            return 100.0
        
        # Penalize short-term gains and wash sales
        long_term_ratio = long_term_gains / total_gains if total_gains > 0 else 0
        wash_sale_penalty = min(wash_sale_adjustments / abs(total_gains), 0.5) if total_gains != 0 else 0
        
        efficiency = (long_term_ratio * 100) - (wash_sale_penalty * 50)
        return max(0, min(100, efficiency))
    
    async def _generate_tax_recommendations(
        self,
        short_term_gains: float,
        long_term_gains: float,
        wash_sale_adjustments: float
    ) -> List[str]:
        """Generate tax optimization recommendations."""
        recommendations = []
        
        if short_term_gains > long_term_gains * 2:
            recommendations.append(
                "Consider holding positions longer to qualify for long-term capital gains treatment"
            )
        
        if wash_sale_adjustments > 0:
            recommendations.append(
                "Avoid repurchasing the same security within 30 days of a loss to prevent wash sale rules"
            )
        
        if short_term_gains > 0 and long_term_gains < 0:
            recommendations.append(
                "Consider harvesting long-term losses to offset short-term gains"
            )
        
        recommendations.append(
            "Focus on ETF trading (SPY, QQQ, IWM) for better tax efficiency than individual stocks"
        )
        
        return recommendations
    
    async def export_tax_data(
        self,
        start_date: datetime,
        end_date: datetime,
        format_type: str = "csv"
    ) -> Dict:
        """Export tax data for external tax software."""
        period_events = [
            event for event in self.taxable_events
            if start_date <= event.trade_date <= end_date
        ]
        
        if format_type.lower() == "csv":
            return await self._export_csv_format(period_events)
        elif format_type.lower() == "pdf":
            return await self._export_pdf_format(period_events)
        else:
            return {"error": f"Unsupported format: {format_type}"}
    
    async def _export_csv_format(self, events: List[TaxableEvent]) -> Dict:
        """Export events in CSV format for tax software."""
        csv_data = []
        
        for event in events:
            csv_data.append({
                "Symbol": event.symbol,
                "Trade Date": event.trade_date.strftime("%Y-%m-%d"),
                "Quantity": event.quantity,
                "Price": f"{event.price:.2f}",
                "Proceeds": f"{event.proceeds:.2f}",
                "Cost Basis": f"{event.cost_basis:.2f}",
                "Gain/Loss": f"{event.gain_loss:.2f}",
                "Gain Type": event.gain_type.value,
                "Wash Sale": "Yes" if event.is_wash_sale else "No",
                "Wash Sale Adjustment": f"{event.wash_sale_adjustment:.2f}"
            })
        
        return {
            "format": "csv",
            "data": csv_data,
            "filename": f"tax_report_{datetime.now().strftime('%Y%m%d')}.csv"
        }
    
    async def _export_pdf_format(self, events: List[TaxableEvent]) -> Dict:
        """Export events in PDF format."""
        # This would generate a PDF report
        # For now, return metadata
        return {
            "format": "pdf",
            "filename": f"tax_report_{datetime.now().strftime('%Y%m%d')}.pdf",
            "events_count": len(events),
            "generated_at": datetime.now().isoformat()
        }

