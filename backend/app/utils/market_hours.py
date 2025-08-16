"""
Market Hours Utility

Comprehensive market hours validation with timezone support,
holiday handling, and extended hours trading.
"""

import logging
from datetime import datetime, time, timezone
from typing import Dict, Optional, Tuple
import pytz
from pandas.tseries.holiday import USFederalHolidayCalendar

logger = logging.getLogger(__name__)

# US Eastern timezone
ET = pytz.timezone('US/Eastern')

# Market hours configuration
MARKET_HOURS = {
    'pre_market_start': time(4, 0),    # 4:00 AM ET
    'market_open': time(9, 30),        # 9:30 AM ET
    'market_close': time(16, 0),       # 4:00 PM ET
    'after_hours_end': time(20, 0),    # 8:00 PM ET
}

# Holiday calendar
holiday_calendar = USFederalHolidayCalendar()


def get_current_et_time() -> datetime:
    """Get current time in Eastern timezone."""
    return datetime.now(ET)


def is_market_holiday(date: Optional[datetime] = None) -> bool:
    """
    Check if given date is a market holiday.
    
    Args:
        date: Date to check (defaults to today)
        
    Returns:
        bool: True if market holiday
    """
    if date is None:
        date = get_current_et_time().date()
    
    try:
        holidays = holiday_calendar.holidays(
            start=date,
            end=date,
            return_name=True
        )
        return len(holidays) > 0
    except Exception as e:
        logger.warning(f"Error checking holidays: {e}")
        return False


def is_weekend(date: Optional[datetime] = None) -> bool:
    """
    Check if given date is a weekend.
    
    Args:
        date: Date to check (defaults to today)
        
    Returns:
        bool: True if weekend
    """
    if date is None:
        date = get_current_et_time()
    
    return date.weekday() >= 5  # Saturday = 5, Sunday = 6


def is_market_day(date: Optional[datetime] = None) -> bool:
    """
    Check if given date is a valid trading day.
    
    Args:
        date: Date to check (defaults to today)
        
    Returns:
        bool: True if valid trading day
    """
    if date is None:
        date = get_current_et_time()
    
    return not (is_weekend(date) or is_market_holiday(date))


def get_market_session(dt: Optional[datetime] = None) -> str:
    """
    Get current market session.
    
    Args:
        dt: Datetime to check (defaults to now)
        
    Returns:
        str: Market session ('closed', 'pre_market', 'regular', 'after_hours')
    """
    if dt is None:
        dt = get_current_et_time()
    
    # Convert to ET if not already
    if dt.tzinfo != ET:
        dt = dt.astimezone(ET)
    
    current_time = dt.time()
    
    # Check if it's a trading day
    if not is_market_day(dt):
        return 'closed'
    
    # Determine session based on time
    if current_time < MARKET_HOURS['pre_market_start']:
        return 'closed'
    elif current_time < MARKET_HOURS['market_open']:
        return 'pre_market'
    elif current_time < MARKET_HOURS['market_close']:
        return 'regular'
    elif current_time < MARKET_HOURS['after_hours_end']:
        return 'after_hours'
    else:
        return 'closed'


def is_market_open(dt: Optional[datetime] = None, include_extended: bool = False) -> bool:
    """
    Check if market is currently open.
    
    Args:
        dt: Datetime to check (defaults to now)
        include_extended: Include pre-market and after-hours
        
    Returns:
        bool: True if market is open
    """
    session = get_market_session(dt)
    
    if include_extended:
        return session in ['pre_market', 'regular', 'after_hours']
    else:
        return session == 'regular'


def get_next_market_open(dt: Optional[datetime] = None) -> datetime:
    """
    Get the next market open time.
    
    Args:
        dt: Reference datetime (defaults to now)
        
    Returns:
        datetime: Next market open time in ET
    """
    if dt is None:
        dt = get_current_et_time()
    
    # Convert to ET if not already
    if dt.tzinfo != ET:
        dt = dt.astimezone(ET)
    
    # Start with today's market open
    next_open = dt.replace(
        hour=MARKET_HOURS['market_open'].hour,
        minute=MARKET_HOURS['market_open'].minute,
        second=0,
        microsecond=0
    )
    
    # If we're past today's open or it's not a trading day, move to next day
    while next_open <= dt or not is_market_day(next_open):
        next_open = next_open.replace(hour=0, minute=0) + timedelta(days=1)
        next_open = next_open.replace(
            hour=MARKET_HOURS['market_open'].hour,
            minute=MARKET_HOURS['market_open'].minute
        )
    
    return next_open


def get_next_market_close(dt: Optional[datetime] = None) -> datetime:
    """
    Get the next market close time.
    
    Args:
        dt: Reference datetime (defaults to now)
        
    Returns:
        datetime: Next market close time in ET
    """
    if dt is None:
        dt = get_current_et_time()
    
    # Convert to ET if not already
    if dt.tzinfo != ET:
        dt = dt.astimezone(ET)
    
    # Start with today's market close
    next_close = dt.replace(
        hour=MARKET_HOURS['market_close'].hour,
        minute=MARKET_HOURS['market_close'].minute,
        second=0,
        microsecond=0
    )
    
    # If we're past today's close or it's not a trading day, move to next trading day
    while next_close <= dt or not is_market_day(next_close):
        next_close = next_close.replace(hour=0, minute=0) + timedelta(days=1)
        next_close = next_close.replace(
            hour=MARKET_HOURS['market_close'].hour,
            minute=MARKET_HOURS['market_close'].minute
        )
    
    return next_close


def get_market_status() -> Dict[str, any]:
    """
    Get comprehensive market status information.
    
    Returns:
        dict: Market status information
    """
    now = get_current_et_time()
    session = get_market_session(now)
    
    return {
        'timestamp': now.isoformat(),
        'session': session,
        'is_open': session == 'regular',
        'is_extended_hours': session in ['pre_market', 'after_hours'],
        'is_trading_day': is_market_day(now),
        'is_holiday': is_market_holiday(now),
        'is_weekend': is_weekend(now),
        'next_open': get_next_market_open(now).isoformat(),
        'next_close': get_next_market_close(now).isoformat(),
        'market_hours': {
            'pre_market_start': MARKET_HOURS['pre_market_start'].strftime('%H:%M'),
            'market_open': MARKET_HOURS['market_open'].strftime('%H:%M'),
            'market_close': MARKET_HOURS['market_close'].strftime('%H:%M'),
            'after_hours_end': MARKET_HOURS['after_hours_end'].strftime('%H:%M'),
        }
    }


def validate_trading_time(dt: Optional[datetime] = None, allow_extended: bool = False) -> Tuple[bool, str]:
    """
    Validate if trading is allowed at given time.
    
    Args:
        dt: Datetime to validate (defaults to now)
        allow_extended: Allow extended hours trading
        
    Returns:
        tuple: (is_valid, reason)
    """
    if dt is None:
        dt = get_current_et_time()
    
    session = get_market_session(dt)
    
    if session == 'closed':
        if is_weekend(dt):
            return False, "Market closed: Weekend"
        elif is_market_holiday(dt):
            return False, "Market closed: Holiday"
        else:
            return False, "Market closed: Outside trading hours"
    
    if session == 'regular':
        return True, "Regular market hours"
    
    if session in ['pre_market', 'after_hours']:
        if allow_extended:
            return True, f"Extended hours: {session}"
        else:
            return False, f"Outside regular hours: {session}"
    
    return False, f"Unknown session: {session}"


# Convenience functions for common checks
def is_regular_hours(dt: Optional[datetime] = None) -> bool:
    """Check if it's regular market hours."""
    return get_market_session(dt) == 'regular'


def is_pre_market(dt: Optional[datetime] = None) -> bool:
    """Check if it's pre-market hours."""
    return get_market_session(dt) == 'pre_market'


def is_after_hours(dt: Optional[datetime] = None) -> bool:
    """Check if it's after-hours trading."""
    return get_market_session(dt) == 'after_hours'


def is_extended_hours(dt: Optional[datetime] = None) -> bool:
    """Check if it's extended hours (pre-market or after-hours)."""
    session = get_market_session(dt)
    return session in ['pre_market', 'after_hours']

