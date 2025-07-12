"""
Smart-0DTE-System Monitoring Service

This module implements comprehensive system monitoring, health checks,
performance tracking, and alerting capabilities.
"""

import asyncio
import logging
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json

from app.core.config import settings
from app.core.redis_client import market_data_cache
from app.core.database import get_db_session
from app.services.risk_management_service import risk_management_service

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service status enumeration."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"


@dataclass
class SystemMetrics:
    """System performance metrics."""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, int]
    active_connections: int
    uptime: float
    timestamp: datetime


@dataclass
class ServiceHealth:
    """Service health information."""
    name: str
    status: ServiceStatus
    last_check: datetime
    response_time: float
    error_count: int
    details: Dict[str, Any]


class MonitoringService:
    """
    Comprehensive System Monitoring Service
    
    Monitors system health, performance metrics, service availability,
    and provides real-time alerting and dashboard data.
    """
    
    def __init__(self):
        self.is_running = False
        self.start_time = datetime.utcnow()
        
        # Service registry
        self.services = {
            'market_data': {'endpoint': '/api/v1/market-data/health', 'timeout': 5},
            'intelligence': {'endpoint': '/api/v1/intelligence/health', 'timeout': 5},
            'trading': {'endpoint': '/api/v1/trading/health', 'timeout': 5},
            'risk_management': {'endpoint': '/api/v1/risk/health', 'timeout': 5},
            'ibkr': {'endpoint': '/api/v1/ibkr/health', 'timeout': 10},
            'database': {'endpoint': '/api/v1/db/health', 'timeout': 5},
            'redis': {'endpoint': '/api/v1/cache/health', 'timeout': 5}
        }
        
        # Health status tracking
        self.service_health = {}
        self.system_metrics_history = []
        self.alert_history = []
        
        # Performance thresholds
        self.cpu_warning_threshold = 80.0
        self.cpu_critical_threshold = 95.0
        self.memory_warning_threshold = 85.0
        self.memory_critical_threshold = 95.0
        self.disk_warning_threshold = 90.0
        self.disk_critical_threshold = 98.0
        
        # Monitoring intervals
        self.health_check_interval = 30  # seconds
        self.metrics_collection_interval = 60  # seconds
        self.alert_check_interval = 15  # seconds
        
    async def initialize(self) -> None:
        """Initialize Monitoring Service."""
        try:
            # Initialize service health tracking
            for service_name in self.services.keys():
                self.service_health[service_name] = ServiceHealth(
                    name=service_name,
                    status=ServiceStatus.OFFLINE,
                    last_check=datetime.utcnow(),
                    response_time=0.0,
                    error_count=0,
                    details={}
                )
            
            logger.info("Monitoring Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Monitoring Service: {e}")
            raise
    
    async def start_monitoring(self) -> None:
        """Start all monitoring processes."""
        try:
            self.is_running = True
            
            # Start monitoring tasks
            asyncio.create_task(self._monitor_system_metrics())
            asyncio.create_task(self._monitor_service_health())
            asyncio.create_task(self._monitor_trading_performance())
            asyncio.create_task(self._monitor_data_feeds())
            asyncio.create_task(self._generate_alerts())
            asyncio.create_task(self._cleanup_old_data())
            
            logger.info("System monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            raise
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring processes."""
        try:
            self.is_running = False
            
            # Save final metrics
            await self._save_monitoring_data()
            
            logger.info("System monitoring stopped")
            
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}")
    
    async def _monitor_system_metrics(self) -> None:
        """Monitor system performance metrics."""
        while self.is_running:
            try:
                # Collect system metrics
                metrics = await self._collect_system_metrics()
                
                # Store metrics
                self.system_metrics_history.append(metrics)
                
                # Cache current metrics
                await market_data_cache.redis.set(
                    'system_metrics',
                    {
                        'cpu_usage': metrics.cpu_usage,
                        'memory_usage': metrics.memory_usage,
                        'disk_usage': metrics.disk_usage,
                        'network_io': metrics.network_io,
                        'active_connections': metrics.active_connections,
                        'uptime': metrics.uptime,
                        'timestamp': metrics.timestamp.isoformat()
                    },
                    ttl=300
                )
                
                # Check thresholds and generate alerts
                await self._check_system_thresholds(metrics)
                
                # Keep only last 24 hours of metrics
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                self.system_metrics_history = [
                    m for m in self.system_metrics_history
                    if m.timestamp > cutoff_time
                ]
                
                await asyncio.sleep(self.metrics_collection_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring system metrics: {e}")
                await asyncio.sleep(30)
    
    async def _monitor_service_health(self) -> None:
        """Monitor health of all services."""
        while self.is_running:
            try:
                for service_name, config in self.services.items():
                    health = await self._check_service_health(service_name, config)
                    self.service_health[service_name] = health
                
                # Cache service health summary
                health_summary = {
                    name: {
                        'status': health.status.value,
                        'last_check': health.last_check.isoformat(),
                        'response_time': health.response_time,
                        'error_count': health.error_count
                    }
                    for name, health in self.service_health.items()
                }
                
                await market_data_cache.redis.set(
                    'service_health',
                    health_summary,
                    ttl=300
                )
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring service health: {e}")
                await asyncio.sleep(30)
    
    async def _monitor_trading_performance(self) -> None:
        """Monitor trading system performance."""
        while self.is_running:
            try:
                # Get performance metrics from risk management service
                performance = await risk_management_service.get_performance_summary()
                
                # Get current positions and P&L
                risk_status = await risk_management_service.get_current_risk_status()
                
                # Combine trading metrics
                trading_metrics = {
                    'performance': performance,
                    'risk_status': risk_status,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # Cache trading metrics
                await market_data_cache.redis.set(
                    'trading_metrics',
                    trading_metrics,
                    ttl=300
                )
                
                # Check for trading alerts
                await self._check_trading_alerts(trading_metrics)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error monitoring trading performance: {e}")
                await asyncio.sleep(30)
    
    async def _monitor_data_feeds(self) -> None:
        """Monitor data feed health and latency."""
        while self.is_running:
            try:
                data_feed_status = {}
                
                # Check market data feeds
                for symbol in ['SPY', 'QQQ', 'IWM']:
                    market_data = await market_data_cache.redis.get(f'market_data_{symbol}')
                    
                    if market_data:
                        timestamp = market_data.get('timestamp')
                        if timestamp:
                            last_update = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            latency = (datetime.utcnow() - last_update.replace(tzinfo=None)).total_seconds()
                            
                            data_feed_status[symbol] = {
                                'status': 'healthy' if latency < 60 else 'stale',
                                'latency': latency,
                                'last_update': timestamp
                            }
                        else:
                            data_feed_status[symbol] = {
                                'status': 'no_data',
                                'latency': None,
                                'last_update': None
                            }
                    else:
                        data_feed_status[symbol] = {
                            'status': 'offline',
                            'latency': None,
                            'last_update': None
                        }
                
                # Check VIX data
                vix_data = await market_data_cache.redis.get('vix_data')
                if vix_data:
                    timestamp = vix_data.get('timestamp')
                    if timestamp:
                        last_update = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        latency = (datetime.utcnow() - last_update.replace(tzinfo=None)).total_seconds()
                        
                        data_feed_status['VIX'] = {
                            'status': 'healthy' if latency < 300 else 'stale',  # VIX updates less frequently
                            'latency': latency,
                            'last_update': timestamp
                        }
                
                # Cache data feed status
                await market_data_cache.redis.set(
                    'data_feed_status',
                    data_feed_status,
                    ttl=300
                )
                
                # Check for data feed alerts
                await self._check_data_feed_alerts(data_feed_status)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error monitoring data feeds: {e}")
                await asyncio.sleep(30)
    
    async def _generate_alerts(self) -> None:
        """Generate and manage system alerts."""
        while self.is_running:
            try:
                # Check for system-wide issues
                await self._check_system_alerts()
                
                # Clean up old alerts
                await self._cleanup_old_alerts()
                
                await asyncio.sleep(self.alert_check_interval)
                
            except Exception as e:
                logger.error(f"Error generating alerts: {e}")
                await asyncio.sleep(30)
    
    async def _cleanup_old_data(self) -> None:
        """Clean up old monitoring data."""
        while self.is_running:
            try:
                # Clean up metrics history (keep last 24 hours)
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                
                self.system_metrics_history = [
                    m for m in self.system_metrics_history
                    if m.timestamp > cutoff_time
                ]
                
                # Clean up alert history (keep last 7 days)
                alert_cutoff = datetime.utcnow() - timedelta(days=7)
                self.alert_history = [
                    a for a in self.alert_history
                    if datetime.fromisoformat(a['timestamp']) > alert_cutoff
                ]
                
                await asyncio.sleep(3600)  # Clean up every hour
                
            except Exception as e:
                logger.error(f"Error cleaning up old data: {e}")
                await asyncio.sleep(300)
    
    async def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system performance metrics."""
        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage = (disk.used / disk.total) * 100
            
            # Network I/O
            network = psutil.net_io_counters()
            network_io = {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            }
            
            # Active connections (approximate)
            connections = len(psutil.net_connections())
            
            # System uptime
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
            
            return SystemMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                network_io=network_io,
                active_connections=connections,
                uptime=uptime,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics(
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                network_io={},
                active_connections=0,
                uptime=0.0,
                timestamp=datetime.utcnow()
            )
    
    async def _check_service_health(self, service_name: str, config: Dict[str, Any]) -> ServiceHealth:
        """Check health of a specific service."""
        try:
            start_time = time.time()
            
            # For now, simulate health checks
            # In a real implementation, this would make HTTP requests to service endpoints
            
            if service_name == 'risk_management':
                # Check risk management service directly
                is_healthy = await risk_management_service.health_check()
                status = ServiceStatus.HEALTHY if is_healthy else ServiceStatus.CRITICAL
            else:
                # Simulate other service checks
                status = ServiceStatus.HEALTHY
            
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            current_health = self.service_health.get(service_name)
            error_count = current_health.error_count if current_health else 0
            
            if status != ServiceStatus.HEALTHY:
                error_count += 1
            else:
                error_count = max(0, error_count - 1)  # Gradually reduce error count
            
            return ServiceHealth(
                name=service_name,
                status=status,
                last_check=datetime.utcnow(),
                response_time=response_time,
                error_count=error_count,
                details={'endpoint': config.get('endpoint', ''), 'timeout': config.get('timeout', 5)}
            )
            
        except Exception as e:
            logger.error(f"Error checking {service_name} health: {e}")
            
            current_health = self.service_health.get(service_name)
            error_count = (current_health.error_count if current_health else 0) + 1
            
            return ServiceHealth(
                name=service_name,
                status=ServiceStatus.CRITICAL,
                last_check=datetime.utcnow(),
                response_time=0.0,
                error_count=error_count,
                details={'error': str(e)}
            )
    
    async def _check_system_thresholds(self, metrics: SystemMetrics) -> None:
        """Check system metrics against thresholds and generate alerts."""
        try:
            alerts = []
            
            # CPU usage alerts
            if metrics.cpu_usage >= self.cpu_critical_threshold:
                alerts.append({
                    'type': 'system_cpu_critical',
                    'severity': 'critical',
                    'title': 'Critical CPU Usage',
                    'message': f'CPU usage: {metrics.cpu_usage:.1f}%',
                    'value': metrics.cpu_usage
                })
            elif metrics.cpu_usage >= self.cpu_warning_threshold:
                alerts.append({
                    'type': 'system_cpu_warning',
                    'severity': 'warning',
                    'title': 'High CPU Usage',
                    'message': f'CPU usage: {metrics.cpu_usage:.1f}%',
                    'value': metrics.cpu_usage
                })
            
            # Memory usage alerts
            if metrics.memory_usage >= self.memory_critical_threshold:
                alerts.append({
                    'type': 'system_memory_critical',
                    'severity': 'critical',
                    'title': 'Critical Memory Usage',
                    'message': f'Memory usage: {metrics.memory_usage:.1f}%',
                    'value': metrics.memory_usage
                })
            elif metrics.memory_usage >= self.memory_warning_threshold:
                alerts.append({
                    'type': 'system_memory_warning',
                    'severity': 'warning',
                    'title': 'High Memory Usage',
                    'message': f'Memory usage: {metrics.memory_usage:.1f}%',
                    'value': metrics.memory_usage
                })
            
            # Disk usage alerts
            if metrics.disk_usage >= self.disk_critical_threshold:
                alerts.append({
                    'type': 'system_disk_critical',
                    'severity': 'critical',
                    'title': 'Critical Disk Usage',
                    'message': f'Disk usage: {metrics.disk_usage:.1f}%',
                    'value': metrics.disk_usage
                })
            elif metrics.disk_usage >= self.disk_warning_threshold:
                alerts.append({
                    'type': 'system_disk_warning',
                    'severity': 'warning',
                    'title': 'High Disk Usage',
                    'message': f'Disk usage: {metrics.disk_usage:.1f}%',
                    'value': metrics.disk_usage
                })
            
            # Store alerts
            for alert in alerts:
                await self._store_alert(alert)
            
        except Exception as e:
            logger.error(f"Error checking system thresholds: {e}")
    
    async def _check_trading_alerts(self, trading_metrics: Dict[str, Any]) -> None:
        """Check trading metrics for alert conditions."""
        try:
            alerts = []
            
            risk_status = trading_metrics.get('risk_status', {})
            performance = trading_metrics.get('performance', {})
            
            # Emergency halt alert
            if risk_status.get('emergency_halt_active'):
                alerts.append({
                    'type': 'trading_emergency_halt',
                    'severity': 'critical',
                    'title': 'Trading Emergency Halt Active',
                    'message': 'All trading activities have been halted',
                    'value': True
                })
            
            # Daily P&L alerts
            daily_pnl = risk_status.get('daily_pnl', 0)
            if daily_pnl <= -500:  # Significant loss
                alerts.append({
                    'type': 'trading_daily_loss',
                    'severity': 'high' if daily_pnl <= -1000 else 'warning',
                    'title': 'Significant Daily Loss',
                    'message': f'Daily P&L: ${daily_pnl:.2f}',
                    'value': daily_pnl
                })
            
            # Win rate alerts
            win_rate = performance.get('win_rate', 0)
            if win_rate < 0.4:  # Low win rate
                alerts.append({
                    'type': 'trading_low_win_rate',
                    'severity': 'warning',
                    'title': 'Low Win Rate',
                    'message': f'Win rate: {win_rate:.1%}',
                    'value': win_rate
                })
            
            # Store alerts
            for alert in alerts:
                await self._store_alert(alert)
            
        except Exception as e:
            logger.error(f"Error checking trading alerts: {e}")
    
    async def _check_data_feed_alerts(self, data_feed_status: Dict[str, Any]) -> None:
        """Check data feed status for alert conditions."""
        try:
            alerts = []
            
            for symbol, status in data_feed_status.items():
                feed_status = status.get('status')
                latency = status.get('latency')
                
                if feed_status == 'offline':
                    alerts.append({
                        'type': 'data_feed_offline',
                        'severity': 'critical',
                        'title': f'{symbol} Data Feed Offline',
                        'message': f'{symbol} market data feed is not responding',
                        'value': symbol
                    })
                elif feed_status == 'stale':
                    alerts.append({
                        'type': 'data_feed_stale',
                        'severity': 'warning',
                        'title': f'{symbol} Data Feed Stale',
                        'message': f'{symbol} data is {latency:.0f} seconds old',
                        'value': latency
                    })
                elif latency and latency > 30:  # High latency
                    alerts.append({
                        'type': 'data_feed_latency',
                        'severity': 'warning',
                        'title': f'{symbol} High Data Latency',
                        'message': f'{symbol} data latency: {latency:.1f}s',
                        'value': latency
                    })
            
            # Store alerts
            for alert in alerts:
                await self._store_alert(alert)
            
        except Exception as e:
            logger.error(f"Error checking data feed alerts: {e}")
    
    async def _check_system_alerts(self) -> None:
        """Check for system-wide alert conditions."""
        try:
            alerts = []
            
            # Check service health
            critical_services = [
                name for name, health in self.service_health.items()
                if health.status == ServiceStatus.CRITICAL
            ]
            
            if critical_services:
                alerts.append({
                    'type': 'services_critical',
                    'severity': 'critical',
                    'title': 'Critical Services Down',
                    'message': f'Services offline: {", ".join(critical_services)}',
                    'value': critical_services
                })
            
            # Check overall system health
            healthy_services = sum(
                1 for health in self.service_health.values()
                if health.status == ServiceStatus.HEALTHY
            )
            total_services = len(self.service_health)
            
            if total_services > 0:
                health_ratio = healthy_services / total_services
                if health_ratio < 0.5:  # Less than 50% services healthy
                    alerts.append({
                        'type': 'system_health_degraded',
                        'severity': 'high',
                        'title': 'System Health Degraded',
                        'message': f'Only {healthy_services}/{total_services} services healthy',
                        'value': health_ratio
                    })
            
            # Store alerts
            for alert in alerts:
                await self._store_alert(alert)
            
        except Exception as e:
            logger.error(f"Error checking system alerts: {e}")
    
    async def _store_alert(self, alert: Dict[str, Any]) -> None:
        """Store an alert in the system."""
        try:
            alert_id = f"{alert['type']}_{int(datetime.utcnow().timestamp())}"
            
            full_alert = {
                'id': alert_id,
                'timestamp': datetime.utcnow().isoformat(),
                **alert
            }
            
            # Add to alert history
            self.alert_history.append(full_alert)
            
            # Cache alert
            await market_data_cache.redis.set(
                f"monitoring_alert:{alert_id}",
                full_alert,
                ttl=3600
            )
            
            # Log alert
            severity = alert.get('severity', 'info')
            title = alert.get('title', 'System Alert')
            message = alert.get('message', '')
            
            if severity == 'critical':
                logger.critical(f"CRITICAL ALERT: {title} - {message}")
            elif severity == 'high':
                logger.error(f"HIGH ALERT: {title} - {message}")
            elif severity == 'warning':
                logger.warning(f"WARNING: {title} - {message}")
            else:
                logger.info(f"INFO: {title} - {message}")
            
        except Exception as e:
            logger.error(f"Error storing alert: {e}")
    
    async def _cleanup_old_alerts(self) -> None:
        """Clean up old alerts."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            
            self.alert_history = [
                alert for alert in self.alert_history
                if datetime.fromisoformat(alert['timestamp']) > cutoff_time
            ]
            
        except Exception as e:
            logger.error(f"Error cleaning up alerts: {e}")
    
    async def _save_monitoring_data(self) -> None:
        """Save monitoring data before shutdown."""
        try:
            # Save current state to cache
            monitoring_state = {
                'service_health': {
                    name: {
                        'status': health.status.value,
                        'last_check': health.last_check.isoformat(),
                        'response_time': health.response_time,
                        'error_count': health.error_count,
                        'details': health.details
                    }
                    for name, health in self.service_health.items()
                },
                'alert_count': len(self.alert_history),
                'uptime': (datetime.utcnow() - self.start_time).total_seconds(),
                'shutdown_time': datetime.utcnow().isoformat()
            }
            
            await market_data_cache.redis.set(
                'monitoring_state',
                monitoring_state,
                ttl=86400
            )
            
            logger.info("Monitoring data saved")
            
        except Exception as e:
            logger.error(f"Error saving monitoring data: {e}")
    
    # Public API methods
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        try:
            # Get latest metrics
            latest_metrics = self.system_metrics_history[-1] if self.system_metrics_history else None
            
            # Calculate service health summary
            service_summary = {}
            for status in ServiceStatus:
                service_summary[status.value] = sum(
                    1 for health in self.service_health.values()
                    if health.status == status
                )
            
            # Get recent alerts
            recent_alerts = [
                alert for alert in self.alert_history
                if datetime.fromisoformat(alert['timestamp']) > datetime.utcnow() - timedelta(hours=1)
            ]
            
            return {
                'overall_status': self._calculate_overall_status(),
                'uptime': (datetime.utcnow() - self.start_time).total_seconds(),
                'system_metrics': {
                    'cpu_usage': latest_metrics.cpu_usage if latest_metrics else 0,
                    'memory_usage': latest_metrics.memory_usage if latest_metrics else 0,
                    'disk_usage': latest_metrics.disk_usage if latest_metrics else 0,
                    'active_connections': latest_metrics.active_connections if latest_metrics else 0
                } if latest_metrics else {},
                'service_health': service_summary,
                'recent_alerts': len(recent_alerts),
                'emergency_halt': await self._check_emergency_status(),
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {}
    
    async def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed system metrics and health information."""
        try:
            return {
                'system_metrics': [
                    {
                        'cpu_usage': m.cpu_usage,
                        'memory_usage': m.memory_usage,
                        'disk_usage': m.disk_usage,
                        'network_io': m.network_io,
                        'active_connections': m.active_connections,
                        'timestamp': m.timestamp.isoformat()
                    }
                    for m in self.system_metrics_history[-60:]  # Last hour
                ],
                'service_health': {
                    name: {
                        'status': health.status.value,
                        'last_check': health.last_check.isoformat(),
                        'response_time': health.response_time,
                        'error_count': health.error_count,
                        'details': health.details
                    }
                    for name, health in self.service_health.items()
                },
                'recent_alerts': self.alert_history[-50:],  # Last 50 alerts
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting detailed metrics: {e}")
            return {}
    
    def _calculate_overall_status(self) -> str:
        """Calculate overall system status."""
        try:
            critical_count = sum(
                1 for health in self.service_health.values()
                if health.status == ServiceStatus.CRITICAL
            )
            
            warning_count = sum(
                1 for health in self.service_health.values()
                if health.status == ServiceStatus.WARNING
            )
            
            if critical_count > 0:
                return 'critical'
            elif warning_count > 0:
                return 'warning'
            else:
                return 'healthy'
                
        except Exception as e:
            logger.error(f"Error calculating overall status: {e}")
            return 'unknown'
    
    async def _check_emergency_status(self) -> bool:
        """Check if emergency halt is active."""
        try:
            emergency_status = await market_data_cache.redis.get('emergency_halt_status')
            return emergency_status.get('active', False) if emergency_status else False
            
        except Exception as e:
            logger.error(f"Error checking emergency status: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check monitoring service health."""
        try:
            return self.is_running and (datetime.utcnow() - self.start_time).total_seconds() > 0
            
        except Exception as e:
            logger.error(f"Monitoring Service health check failed: {e}")
            return False


# Global monitoring service instance
monitoring_service = MonitoringService()

