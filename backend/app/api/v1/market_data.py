"""
Market Data API Endpoints for Smart-0DTE-System
RESTful API for accessing ETF/VIX market data, options chains, and analytics

Optimized for SPY, QQQ, IWM, and VIX focused trading system.
"""

from fastapi import APIRouter, HTTPException, Query, Depends, WebSocket
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
import json
import asyncio
from pydantic import BaseModel

from ...models.market_data import Symbol, MarketDataPoint, OHLCData, OptionsData, VIXData, CorrelationData
from ...services.data_storage_service import get_storage_service, DataStorageService
from ...services.data_feed_service import data_feed_service

router = APIRouter(prefix="/market-data", tags=["market-data"])

# Response Models
class MarketDataResponse(BaseModel):
    symbol: str
    timestamp: str
    price: float
    volume: int
    bid: Optional[float] = None
    ask: Optional[float] = None

class OHLCResponse(BaseModel):
    symbol: str
    timestamp: str
    interval: str
    open: float
    high: float
    low: float
    close: float
    volume: int

class OptionsResponse(BaseModel):
    underlying_symbol: str
    timestamp: str
    expiration: str
    strike: float
    option_type: str
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None

class VIXResponse(BaseModel):
    timestamp: str
    vix_level: float
    vix_change: float
    vix_change_percent: float
    term_structure: Dict[str, float]
    regime: str

class CorrelationResponse(BaseModel):
    timestamp: str
    spy_qqq_correlation: float
    spy_iwm_correlation: float
    qqq_iwm_correlation: float
    spy_vix_correlation: float
    qqq_vix_correlation: float
    iwm_vix_correlation: float
    regime_change_probability: float

class MarketStatusResponse(BaseModel):
    is_market_open: bool
    market_session: str
    next_open: Optional[str] = None
    next_close: Optional[str] = None
    supported_symbols: List[str]
    data_feed_status: Dict[str, Any]

# Market Data Endpoints
@router.get("/status", response_model=MarketStatusResponse)
async def get_market_status():
    """Get current market status and system health"""
    try:
        # Determine market session
        now = datetime.now(timezone.utc)
        market_open_utc = now.replace(hour=14, minute=30, second=0, microsecond=0)  # 9:30 AM EST
        market_close_utc = now.replace(hour=21, minute=0, second=0, microsecond=0)  # 4:00 PM EST
        
        is_market_open = market_open_utc <= now <= market_close_utc
        
        if is_market_open:
            market_session = "regular"
            next_close = market_close_utc.isoformat()
            next_open = None
        else:
            market_session = "closed"
            if now < market_open_utc:
                next_open = market_open_utc.isoformat()
            else:
                # Next day
                next_open = (market_open_utc + timedelta(days=1)).isoformat()
            next_close = None
        
        return MarketStatusResponse(
            is_market_open=is_market_open,
            market_session=market_session,
            next_open=next_open,
            next_close=next_close,
            supported_symbols=[symbol.value for symbol in Symbol],
            data_feed_status=data_feed_service.get_market_status()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting market status: {str(e)}")

@router.get("/realtime/{symbol}", response_model=MarketDataResponse)
async def get_realtime_data(
    symbol: str,
    storage: DataStorageService = Depends(get_storage_service)
):
    """Get latest real-time market data for a symbol"""
    try:
        # Validate symbol
        try:
            symbol_enum = Symbol(symbol.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unsupported symbol: {symbol}")
        
        # Get latest data from storage
        data = await storage.get_latest_market_data(symbol_enum)
        if not data:
            raise HTTPException(status_code=404, detail=f"No data found for symbol: {symbol}")
        
        return MarketDataResponse(
            symbol=data.symbol.value,
            timestamp=data.timestamp.isoformat(),
            price=data.price,
            volume=data.volume,
            bid=data.bid,
            ask=data.ask
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting real-time data: {str(e)}")

@router.get("/realtime", response_model=List[MarketDataResponse])
async def get_all_realtime_data(
    storage: DataStorageService = Depends(get_storage_service)
):
    """Get latest real-time data for all supported symbols"""
    try:
        results = []
        for symbol in [Symbol.SPY, Symbol.QQQ, Symbol.IWM]:  # VIX handled separately
            data = await storage.get_latest_market_data(symbol)
            if data:
                results.append(MarketDataResponse(
                    symbol=data.symbol.value,
                    timestamp=data.timestamp.isoformat(),
                    price=data.price,
                    volume=data.volume,
                    bid=data.bid,
                    ask=data.ask
                ))
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting real-time data: {str(e)}")

@router.get("/history/{symbol}", response_model=List[MarketDataResponse])
async def get_historical_data(
    symbol: str,
    start_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of records"),
    storage: DataStorageService = Depends(get_storage_service)
):
    """Get historical market data for a symbol"""
    try:
        # Validate symbol
        try:
            symbol_enum = Symbol(symbol.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unsupported symbol: {symbol}")
        
        # Set default time range if not provided
        if not end_time:
            end_time = datetime.now(timezone.utc)
        if not start_time:
            start_time = end_time - timedelta(hours=24)  # Last 24 hours
        
        # Get historical data
        data_points = await storage.get_market_data_range(symbol_enum, start_time, end_time)
        
        # Apply limit
        if len(data_points) > limit:
            data_points = data_points[-limit:]  # Get most recent records
        
        return [
            MarketDataResponse(
                symbol=data.symbol.value,
                timestamp=data.timestamp.isoformat(),
                price=data.price,
                volume=data.volume,
                bid=data.bid,
                ask=data.ask
            )
            for data in data_points
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting historical data: {str(e)}")

@router.get("/ohlc/{symbol}", response_model=List[OHLCResponse])
async def get_ohlc_data(
    symbol: str,
    interval: str = Query("1m", description="Time interval (1m, 5m, 15m, 1h, 1d)"),
    start_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    limit: int = Query(500, ge=1, le=5000, description="Maximum number of records"),
    storage: DataStorageService = Depends(get_storage_service)
):
    """Get OHLC data for charting"""
    try:
        # Validate symbol
        try:
            symbol_enum = Symbol(symbol.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unsupported symbol: {symbol}")
        
        # Validate interval
        valid_intervals = ['1m', '5m', '15m', '1h', '1d']
        if interval not in valid_intervals:
            raise HTTPException(status_code=400, detail=f"Invalid interval. Must be one of: {valid_intervals}")
        
        # Set default time range
        if not end_time:
            end_time = datetime.now(timezone.utc)
        if not start_time:
            if interval == '1d':
                start_time = end_time - timedelta(days=30)  # 30 days for daily
            elif interval == '1h':
                start_time = end_time - timedelta(days=7)   # 7 days for hourly
            else:
                start_time = end_time - timedelta(days=1)   # 1 day for minute intervals
        
        # Get OHLC data
        ohlc_data = await storage.get_ohlc_data(symbol_enum, interval, start_time, end_time)
        
        # Apply limit
        if len(ohlc_data) > limit:
            ohlc_data = ohlc_data[-limit:]
        
        return [
            OHLCResponse(
                symbol=data.symbol.value,
                timestamp=data.timestamp.isoformat(),
                interval=data.interval,
                open=data.open,
                high=data.high,
                low=data.low,
                close=data.close,
                volume=data.volume
            )
            for data in ohlc_data
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting OHLC data: {str(e)}")

# Options Data Endpoints
@router.get("/options/{symbol}", response_model=List[OptionsResponse])
async def get_options_chain(
    symbol: str,
    expiration: Optional[str] = Query(None, description="Expiration date (YYYY-MM-DD)"),
    storage: DataStorageService = Depends(get_storage_service)
):
    """Get options chain for a symbol"""
    try:
        # Validate symbol
        try:
            symbol_enum = Symbol(symbol.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unsupported symbol: {symbol}")
        
        # Default to today's expiration if not provided
        if not expiration:
            expiration_date = datetime.now(timezone.utc)
        else:
            try:
                expiration_date = datetime.strptime(expiration, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid expiration date format. Use YYYY-MM-DD")
        
        # Get options chain
        options_data = await storage.get_options_chain(symbol_enum, expiration_date)
        
        return [
            OptionsResponse(
                underlying_symbol=data.underlying_symbol.value,
                timestamp=data.timestamp.isoformat(),
                expiration=data.expiration.date().isoformat(),
                strike=data.strike,
                option_type=data.option_type,
                bid=data.bid,
                ask=data.ask,
                last=data.last,
                volume=data.volume,
                open_interest=data.open_interest,
                implied_volatility=data.implied_volatility,
                delta=data.delta,
                gamma=data.gamma,
                theta=data.theta,
                vega=data.vega
            )
            for data in options_data
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting options chain: {str(e)}")

# VIX Data Endpoints
@router.get("/vix", response_model=VIXResponse)
async def get_vix_data(
    storage: DataStorageService = Depends(get_storage_service)
):
    """Get latest VIX data and volatility regime"""
    try:
        vix_data = await storage.get_latest_vix_data()
        if not vix_data:
            raise HTTPException(status_code=404, detail="No VIX data found")
        
        return VIXResponse(
            timestamp=vix_data.timestamp.isoformat(),
            vix_level=vix_data.vix_level,
            vix_change=vix_data.vix_change,
            vix_change_percent=vix_data.vix_change_percent,
            term_structure=vix_data.term_structure,
            regime=vix_data.regime
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting VIX data: {str(e)}")

# Correlation Data Endpoints
@router.get("/correlations", response_model=CorrelationResponse)
async def get_correlation_data(
    storage: DataStorageService = Depends(get_storage_service)
):
    """Get latest correlation data between ETFs and VIX"""
    try:
        # Get latest correlation data (implement in storage service)
        # For now, return simulated data
        now = datetime.now(timezone.utc)
        
        return CorrelationResponse(
            timestamp=now.isoformat(),
            spy_qqq_correlation=0.85,
            spy_iwm_correlation=0.72,
            qqq_iwm_correlation=0.68,
            spy_vix_correlation=-0.65,
            qqq_vix_correlation=-0.58,
            iwm_vix_correlation=-0.52,
            regime_change_probability=0.25
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting correlation data: {str(e)}")

# WebSocket Endpoint for Real-time Streaming
@router.websocket("/stream")
async def websocket_market_data(websocket: WebSocket):
    """WebSocket endpoint for real-time market data streaming"""
    await websocket.accept()
    
    try:
        # Subscribe to data feed
        async def send_market_data(data: MarketDataPoint):
            await websocket.send_json({
                "type": "market_data",
                "data": data.to_dict()
            })
        
        async def send_vix_data(data: VIXData):
            await websocket.send_json({
                "type": "vix_data", 
                "data": data.to_dict()
            })
        
        # Subscribe to data feeds
        data_feed_service.subscribe('market_data', send_market_data)
        data_feed_service.subscribe('vix_data', send_vix_data)
        
        # Keep connection alive
        while True:
            try:
                # Wait for client messages (ping/pong)
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if message == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat", "timestamp": datetime.now(timezone.utc).isoformat()})
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Unsubscribe from data feeds
        data_feed_service.unsubscribe('market_data', send_market_data)
        data_feed_service.unsubscribe('vix_data', send_vix_data)

# Analytics Endpoints
@router.get("/analytics/summary")
async def get_market_summary():
    """Get market summary with key metrics"""
    try:
        storage = await get_storage_service()
        
        # Get latest data for all symbols
        summary = {}
        for symbol in [Symbol.SPY, Symbol.QQQ, Symbol.IWM]:
            data = await storage.get_latest_market_data(symbol)
            if data:
                summary[symbol.value] = {
                    "price": data.price,
                    "volume": data.volume,
                    "timestamp": data.timestamp.isoformat()
                }
        
        # Get VIX data
        vix_data = await storage.get_latest_vix_data()
        if vix_data:
            summary["VIX"] = {
                "level": vix_data.vix_level,
                "change": vix_data.vix_change,
                "regime": vix_data.regime,
                "timestamp": vix_data.timestamp.isoformat()
            }
        
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting market summary: {str(e)}")

@router.get("/analytics/performance")
async def get_performance_metrics():
    """Get performance metrics for the focused ETF universe"""
    try:
        # Calculate performance metrics (implement based on requirements)
        return {
            "daily_performance": {
                "SPY": {"return": 0.48, "volume_ratio": 1.2},
                "QQQ": {"return": -0.30, "volume_ratio": 0.9},
                "IWM": {"return": 0.40, "volume_ratio": 1.1}
            },
            "volatility_metrics": {
                "VIX": {"level": 16.8, "regime": "low"},
                "realized_vol": {"SPY": 0.12, "QQQ": 0.15, "IWM": 0.18}
            },
            "correlation_strength": {
                "SPY_QQQ": 0.85,
                "SPY_IWM": 0.72,
                "QQQ_IWM": 0.68
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting performance metrics: {str(e)}")

# Export endpoint for data analysis
@router.get("/export/{symbol}")
async def export_data(
    symbol: str,
    format: str = Query("csv", description="Export format (csv, json)"),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    storage: DataStorageService = Depends(get_storage_service)
):
    """Export historical data for analysis"""
    try:
        # Validate symbol
        try:
            symbol_enum = Symbol(symbol.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unsupported symbol: {symbol}")
        
        # Set default time range
        if not end_time:
            end_time = datetime.now(timezone.utc)
        if not start_time:
            start_time = end_time - timedelta(days=7)  # Last week
        
        # Get data
        data_points = await storage.get_market_data_range(symbol_enum, start_time, end_time)
        
        if format.lower() == "csv":
            # Generate CSV
            import io
            import csv
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["timestamp", "symbol", "price", "volume", "bid", "ask"])
            
            for data in data_points:
                writer.writerow([
                    data.timestamp.isoformat(),
                    data.symbol.value,
                    data.price,
                    data.volume,
                    data.bid or "",
                    data.ask or ""
                ])
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={symbol}_data.csv"}
            )
        
        elif format.lower() == "json":
            # Generate JSON
            json_data = [data.to_dict() for data in data_points]
            return StreamingResponse(
                io.BytesIO(json.dumps(json_data, indent=2).encode()),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={symbol}_data.json"}
            )
        
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use 'csv' or 'json'")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting data: {str(e)}")

import logging
logger = logging.getLogger(__name__)

