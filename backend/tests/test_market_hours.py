"""
Tests for Market Hours Utility

Comprehensive test suite for market hours validation,
timezone handling, and holiday detection.
"""

import pytest
from datetime import datetime, time, timezone
from unittest.mock import patch, MagicMock
import pytz

from app.utils.market_hours import (
    get_current_et_time,
    is_market_holiday,
    is_weekend,
    is_market_day,
    get_market_session,
    is_market_open,
    get_next_market_open,
    get_next_market_close,
    get_market_status,
    validate_trading_time,
    is_regular_hours,
    is_pre_market,
    is_after_hours,
    is_extended_hours,
    MARKET_HOURS,
    ET
)


class TestMarketHours:
    """Test market hours functionality."""
    
    def test_get_current_et_time(self):
        """Test getting current ET time."""
        et_time = get_current_et_time()
        assert et_time.tzinfo == ET
        assert isinstance(et_time, datetime)
    
    def test_is_weekend(self):
        """Test weekend detection."""
        # Saturday
        saturday = datetime(2024, 1, 6, 12, 0, tzinfo=ET)  # Saturday
        assert is_weekend(saturday) is True
        
        # Sunday
        sunday = datetime(2024, 1, 7, 12, 0, tzinfo=ET)  # Sunday
        assert is_weekend(sunday) is True
        
        # Monday
        monday = datetime(2024, 1, 8, 12, 0, tzinfo=ET)  # Monday
        assert is_weekend(monday) is False
        
        # Friday
        friday = datetime(2024, 1, 5, 12, 0, tzinfo=ET)  # Friday
        assert is_weekend(friday) is False
    
    @patch('app.utils.market_hours.holiday_calendar')
    def test_is_market_holiday(self, mock_calendar):
        """Test holiday detection."""
        # Mock holiday calendar
        mock_holidays = MagicMock()
        mock_holidays.__len__ = MagicMock(return_value=1)
        mock_calendar.holidays.return_value = mock_holidays
        
        test_date = datetime(2024, 1, 1)  # New Year's Day
        assert is_market_holiday(test_date) is True
        
        # Mock no holidays
        mock_holidays.__len__ = MagicMock(return_value=0)
        mock_calendar.holidays.return_value = mock_holidays
        
        regular_date = datetime(2024, 1, 2)
        assert is_market_holiday(regular_date) is False
    
    def test_is_market_day(self):
        """Test market day validation."""
        # Regular weekday (not holiday)
        with patch('app.utils.market_hours.is_weekend', return_value=False), \
             patch('app.utils.market_hours.is_market_holiday', return_value=False):
            weekday = datetime(2024, 1, 8, 12, 0, tzinfo=ET)  # Monday
            assert is_market_day(weekday) is True
        
        # Weekend
        with patch('app.utils.market_hours.is_weekend', return_value=True):
            weekend = datetime(2024, 1, 6, 12, 0, tzinfo=ET)  # Saturday
            assert is_market_day(weekend) is False
        
        # Holiday
        with patch('app.utils.market_hours.is_weekend', return_value=False), \
             patch('app.utils.market_hours.is_market_holiday', return_value=True):
            holiday = datetime(2024, 1, 1, 12, 0, tzinfo=ET)  # New Year's
            assert is_market_day(holiday) is False
    
    def test_get_market_session(self):
        """Test market session detection."""
        # Test different times on a trading day
        trading_day = datetime(2024, 1, 8, tzinfo=ET)  # Monday
        
        with patch('app.utils.market_hours.is_market_day', return_value=True):
            # Before pre-market (3:00 AM)
            early_morning = trading_day.replace(hour=3, minute=0)
            assert get_market_session(early_morning) == 'closed'
            
            # Pre-market (5:00 AM)
            pre_market = trading_day.replace(hour=5, minute=0)
            assert get_market_session(pre_market) == 'pre_market'
            
            # Regular hours (12:00 PM)
            regular_hours = trading_day.replace(hour=12, minute=0)
            assert get_market_session(regular_hours) == 'regular'
            
            # After hours (18:00 PM)
            after_hours = trading_day.replace(hour=18, minute=0)
            assert get_market_session(after_hours) == 'after_hours'
            
            # Late evening (22:00 PM)
            late_evening = trading_day.replace(hour=22, minute=0)
            assert get_market_session(late_evening) == 'closed'
        
        # Non-trading day
        with patch('app.utils.market_hours.is_market_day', return_value=False):
            weekend = datetime(2024, 1, 6, 12, 0, tzinfo=ET)  # Saturday
            assert get_market_session(weekend) == 'closed'
    
    def test_is_market_open(self):
        """Test market open detection."""
        trading_day = datetime(2024, 1, 8, tzinfo=ET)  # Monday
        
        with patch('app.utils.market_hours.get_market_session') as mock_session:
            # Regular hours
            mock_session.return_value = 'regular'
            assert is_market_open(trading_day) is True
            assert is_market_open(trading_day, include_extended=True) is True
            
            # Pre-market
            mock_session.return_value = 'pre_market'
            assert is_market_open(trading_day) is False
            assert is_market_open(trading_day, include_extended=True) is True
            
            # After hours
            mock_session.return_value = 'after_hours'
            assert is_market_open(trading_day) is False
            assert is_market_open(trading_day, include_extended=True) is True
            
            # Closed
            mock_session.return_value = 'closed'
            assert is_market_open(trading_day) is False
            assert is_market_open(trading_day, include_extended=False) is False
    
    def test_get_next_market_open(self):
        """Test getting next market open time."""
        # Test from before market open on trading day
        with patch('app.utils.market_hours.is_market_day', return_value=True):
            early_morning = datetime(2024, 1, 8, 8, 0, tzinfo=ET)  # Monday 8 AM
            next_open = get_next_market_open(early_morning)
            
            expected = early_morning.replace(
                hour=MARKET_HOURS['market_open'].hour,
                minute=MARKET_HOURS['market_open'].minute,
                second=0,
                microsecond=0
            )
            assert next_open == expected
        
        # Test from after market close
        with patch('app.utils.market_hours.is_market_day') as mock_is_trading_day:
            # Current day is trading day but we're past close
            # Next day is also trading day
            mock_is_trading_day.side_effect = lambda dt: dt.weekday() < 5
            
            after_close = datetime(2024, 1, 8, 17, 0, tzinfo=ET)  # Monday 5 PM
            next_open = get_next_market_open(after_close)
            
            # Should be next day at market open
            expected_date = after_close.date().replace(day=9)  # Tuesday
            expected = datetime.combine(
                expected_date,
                MARKET_HOURS['market_open'],
                tzinfo=ET
            )
            assert next_open.date() == expected.date()
            assert next_open.time() == expected.time()
    
    def test_get_market_status(self):
        """Test comprehensive market status."""
        with patch('app.utils.market_hours.get_current_et_time') as mock_time, \
             patch('app.utils.market_hours.get_market_session') as mock_session, \
             patch('app.utils.market_hours.is_market_day') as mock_is_trading, \
             patch('app.utils.market_hours.is_market_holiday') as mock_is_holiday, \
             patch('app.utils.market_hours.is_weekend') as mock_is_weekend:
            
            test_time = datetime(2024, 1, 8, 12, 0, tzinfo=ET)  # Monday noon
            mock_time.return_value = test_time
            mock_session.return_value = 'regular'
            mock_is_trading.return_value = True
            mock_is_holiday.return_value = False
            mock_is_weekend.return_value = False
            
            status = get_market_status()
            
            assert 'timestamp' in status
            assert status['session'] == 'regular'
            assert status['is_open'] is True
            assert status['is_extended_hours'] is False
            assert status['is_trading_day'] is True
            assert status['is_holiday'] is False
            assert status['is_weekend'] is False
            assert 'next_open' in status
            assert 'next_close' in status
            assert 'market_hours' in status
    
    def test_validate_trading_time(self):
        """Test trading time validation."""
        with patch('app.utils.market_hours.get_market_session') as mock_session:
            # Regular hours
            mock_session.return_value = 'regular'
            is_valid, reason = validate_trading_time()
            assert is_valid is True
            assert "Regular market hours" in reason
            
            # Pre-market with extended allowed
            mock_session.return_value = 'pre_market'
            is_valid, reason = validate_trading_time(allow_extended=True)
            assert is_valid is True
            assert "Extended hours: pre_market" in reason
            
            # Pre-market without extended
            is_valid, reason = validate_trading_time(allow_extended=False)
            assert is_valid is False
            assert "Outside regular hours: pre_market" in reason
            
            # Closed - weekend
            mock_session.return_value = 'closed'
            with patch('app.utils.market_hours.is_weekend', return_value=True):
                is_valid, reason = validate_trading_time()
                assert is_valid is False
                assert "Weekend" in reason
            
            # Closed - holiday
            with patch('app.utils.market_hours.is_weekend', return_value=False), \
                 patch('app.utils.market_hours.is_market_holiday', return_value=True):
                is_valid, reason = validate_trading_time()
                assert is_valid is False
                assert "Holiday" in reason
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        with patch('app.utils.market_hours.get_market_session') as mock_session:
            # Regular hours
            mock_session.return_value = 'regular'
            assert is_regular_hours() is True
            assert is_pre_market() is False
            assert is_after_hours() is False
            assert is_extended_hours() is False
            
            # Pre-market
            mock_session.return_value = 'pre_market'
            assert is_regular_hours() is False
            assert is_pre_market() is True
            assert is_after_hours() is False
            assert is_extended_hours() is True
            
            # After hours
            mock_session.return_value = 'after_hours'
            assert is_regular_hours() is False
            assert is_pre_market() is False
            assert is_after_hours() is True
            assert is_extended_hours() is True
            
            # Closed
            mock_session.return_value = 'closed'
            assert is_regular_hours() is False
            assert is_pre_market() is False
            assert is_after_hours() is False
            assert is_extended_hours() is False
    
    def test_timezone_conversion(self):
        """Test timezone conversion handling."""
        # Test with UTC time
        utc_time = datetime(2024, 1, 8, 17, 0, tzinfo=timezone.utc)  # 5 PM UTC
        session = get_market_session(utc_time)
        
        # Should convert to ET and determine session
        assert isinstance(session, str)
        assert session in ['closed', 'pre_market', 'regular', 'after_hours']
        
        # Test with naive datetime (should work with current ET)
        naive_time = datetime(2024, 1, 8, 12, 0)  # Noon, no timezone
        with patch('app.utils.market_hours.get_current_et_time') as mock_current:
            mock_current.return_value = datetime(2024, 1, 8, 12, 0, tzinfo=ET)
            session = get_market_session(naive_time)
            assert isinstance(session, str)


class TestMarketHoursEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_holiday_calendar_error(self):
        """Test handling of holiday calendar errors."""
        with patch('app.utils.market_hours.holiday_calendar.holidays', side_effect=Exception("API Error")):
            # Should return False and log warning on error
            result = is_market_holiday()
            assert result is False
    
    def test_market_hours_constants(self):
        """Test market hours constants are properly defined."""
        assert 'pre_market_start' in MARKET_HOURS
        assert 'market_open' in MARKET_HOURS
        assert 'market_close' in MARKET_HOURS
        assert 'after_hours_end' in MARKET_HOURS
        
        # Verify times are in correct order
        assert MARKET_HOURS['pre_market_start'] < MARKET_HOURS['market_open']
        assert MARKET_HOURS['market_open'] < MARKET_HOURS['market_close']
        assert MARKET_HOURS['market_close'] < MARKET_HOURS['after_hours_end']
    
    def test_dst_transitions(self):
        """Test behavior during DST transitions."""
        # This is a complex test that would require mocking timezone behavior
        # For now, just ensure the ET timezone is properly configured
        assert ET.zone == 'US/Eastern'
    
    def test_year_boundary(self):
        """Test behavior at year boundaries."""
        # New Year's Eve
        nye = datetime(2023, 12, 31, 15, 0, tzinfo=ET)
        with patch('app.utils.market_hours.is_market_day', return_value=False):
            next_open = get_next_market_open(nye)
            assert next_open.year == 2024
    
    def test_none_datetime_handling(self):
        """Test handling of None datetime parameters."""
        # All functions should handle None by using current time
        with patch('app.utils.market_hours.get_current_et_time') as mock_current:
            mock_current.return_value = datetime(2024, 1, 8, 12, 0, tzinfo=ET)
            
            assert isinstance(is_weekend(None), bool)
            assert isinstance(get_market_session(None), str)
            assert isinstance(is_market_open(None), bool)


if __name__ == "__main__":
    pytest.main([__file__])

