import unittest
import asyncio
from datetime import datetime, date, timedelta
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models.reporting import Report, ReportType, ReportSchedule
from app.services.odte_reporting_service import ODTEReportingService
from app.services.email_service import EmailService
from app.services.scheduler_service import SchedulerService

# Create test client
client = TestClient(app)

# Mock database session
mock_db = MagicMock(spec=Session)

# Override get_db dependency
def override_get_db():
    return mock_db

app.dependency_overrides[get_db] = override_get_db

class TestReporting(unittest.TestCase):
    """Test cases for reporting system."""
    
    def setUp(self):
        """Set up test environment."""
        # Reset mock
        mock_db.reset_mock()
        
        # Create mock report
        self.mock_report = MagicMock()
        self.mock_report.id = 1
        self.mock_report.portfolio_id = 1
        self.mock_report.report_type = ReportType.DAILY
        self.mock_report.start_date = date.today()
        self.mock_report.end_date = date.today()
        self.mock_report.title = "Daily Report"
        self.mock_report.description = "Daily trading report"
        self.mock_report.report_data = {
            "daily_summary": {
                "portfolio_value": 100000,
                "daily_pnl": 1000,
                "daily_pnl_pct": 1.0,
                "signals_generated": 10,
                "signals_executed": 5,
                "total_trades": 8,
                "market_context": {
                    "market_condition": "Normal"
                }
            },
            "next_day_outlook": {
                "market_outlook": "Neutral",
                "expected_volatility": "Normal"
            }
        }
        self.mock_report.pdf_path = "/path/to/report.pdf"
        self.mock_report.created_at = datetime.utcnow()
    
    def test_get_daily_report(self):
        """Test get daily report endpoint."""
        # Mock query
        mock_db.query.return_value.filter.return_value.first.return_value = self.mock_report
        
        # Make request
        response = client.get("/reporting/daily/2023-01-01")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], 1)
        self.assertEqual(response.json()["portfolio_id"], 1)
        self.assertEqual(response.json()["report_type"], "DAILY")
    
    def test_list_reports(self):
        """Test list reports endpoint."""
        # Mock query
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [self.mock_report]
        
        # Make request
        response = client.get("/reporting/list")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["id"], 1)
    
    def test_create_report_schedule(self):
        """Test create report schedule endpoint."""
        # Mock add, commit, refresh
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        
        # Create mock schedule
        mock_schedule = MagicMock()
        mock_schedule.id = 1
        mock_schedule.user_id = 1
        mock_schedule.report_type = ReportType.DAILY
        mock_schedule.is_active = True
        mock_schedule.time_of_day = "18:00"
        mock_schedule.days_of_week = [0, 1, 2, 3, 4]
        mock_schedule.email_delivery = True
        mock_schedule.notification_delivery = False
        mock_schedule.created_at = datetime.utcnow()
        
        # Set mock_db.refresh to update the mock_schedule
        def mock_refresh(obj):
            obj.id = 1
            obj.created_at = datetime.utcnow()
        
        mock_db.refresh.side_effect = mock_refresh
        
        # Make request
        response = client.post(
            "/reporting/schedule",
            json={
                "user_id": 1,
                "report_type": "DAILY",
                "is_active": True,
                "time_of_day": "18:00",
                "days_of_week": [0, 1, 2, 3, 4],
                "email_delivery": True,
                "notification_delivery": False
            }
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_id"], 1)
        self.assertEqual(response.json()["report_type"], "DAILY")
        
        # Check mock calls
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

class TestODTEReportingService(unittest.TestCase):
    """Test cases for ODTE reporting service."""
    
    def setUp(self):
        """Set up test environment."""
        # Reset mock
        mock_db.reset_mock()
        
        # Create reporting service
        self.reporting_service = ODTEReportingService(mock_db)
    
    @patch.object(ODTEReportingService, '_generate_report_data')
    @patch.object(ODTEReportingService, '_generate_pdf')
    def test_generate_daily_report(self, mock_generate_pdf, mock_generate_report_data):
        """Test generate daily report."""
        # Mock report data
        mock_report_data = {
            "daily_summary": {
                "portfolio_value": 100000,
                "daily_pnl": 1000,
                "daily_pnl_pct": 1.0,
                "signals_generated": 10,
                "signals_executed": 5,
                "total_trades": 8,
                "market_context": {
                    "market_condition": "Normal"
                }
            },
            "next_day_outlook": {
                "market_outlook": "Neutral",
                "expected_volatility": "Normal"
            }
        }
        
        # Mock PDF path
        mock_pdf_path = "/path/to/report.pdf"
        
        # Set mock return values
        mock_generate_report_data.return_value = mock_report_data
        mock_generate_pdf.return_value = mock_pdf_path
        
        # Mock query
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Mock add, commit, refresh
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        
        # Create mock report
        mock_report = MagicMock()
        mock_report.id = 1
        
        # Set mock_db.refresh to update the mock_report
        def mock_refresh(obj):
            obj.id = 1
        
        mock_db.refresh.side_effect = mock_refresh
        
        # Call method
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            self.reporting_service.generate_daily_report(date.today(), 1)
        )
        
        # Check result
        self.assertEqual(result, mock_report_data)
        
        # Check mock calls
        mock_generate_report_data.assert_called_once()
        mock_generate_pdf.assert_called_once()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

class TestEmailService(unittest.TestCase):
    """Test cases for email service."""
    
    def setUp(self):
        """Set up test environment."""
        # Create email service
        self.email_service = EmailService()
    
    @patch('smtplib.SMTP')
    def test_send_email(self, mock_smtp):
        """Test send email."""
        # Mock SMTP instance
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
        
        # Set environment variables
        import os
        os.environ["SMTP_USERNAME"] = "test@example.com"
        os.environ["SMTP_PASSWORD"] = "password"
        
        # Call method
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            self.email_service.send_email(
                to_email="user@example.com",
                subject="Test Subject",
                html_content="<p>Test Content</p>",
                text_content="Test Content"
            )
        )
        
        # Check result
        self.assertTrue(result)
        
        # Check mock calls
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with("test@example.com", "password")
        mock_smtp_instance.send_message.assert_called_once()
    
    @patch.object(EmailService, 'send_email')
    def test_send_daily_report_email(self, mock_send_email):
        """Test send daily report email."""
        # Mock send_email
        mock_send_email.return_value = True
        
        # Mock report data
        mock_report_data = {
            "daily_summary": {
                "portfolio_value": 100000,
                "daily_pnl": 1000,
                "daily_pnl_pct": 1.0,
                "signals_generated": 10,
                "signals_executed": 5,
                "total_trades": 8,
                "market_context": {
                    "market_condition": "Normal"
                }
            },
            "next_day_outlook": {
                "market_outlook": "Neutral",
                "expected_volatility": "Normal"
            }
        }
        
        # Call method
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            self.email_service.send_daily_report_email(
                to_email="user@example.com",
                report_date=date.today(),
                report_data=mock_report_data,
                pdf_path="/path/to/report.pdf"
            )
        )
        
        # Check result
        self.assertTrue(result)
        
        # Check mock calls
        mock_send_email.assert_called_once()

class TestSchedulerService(unittest.TestCase):
    """Test cases for scheduler service."""
    
    def setUp(self):
        """Set up test environment."""
        # Create scheduler service
        self.scheduler_service = SchedulerService()
    
    def test_should_run_schedule(self):
        """Test should run schedule."""
        # Create mock schedule
        mock_schedule = MagicMock()
        mock_schedule.days_of_week = [0, 1, 2, 3, 4]  # Monday to Friday
        mock_schedule.time_of_day = "18:00"
        
        # Test with matching day and time
        now = datetime(2023, 1, 2, 18, 0, 0)  # Monday, 18:00
        self.assertTrue(self.scheduler_service._should_run_schedule(mock_schedule, now))
        
        # Test with matching day but different time
        now = datetime(2023, 1, 2, 19, 0, 0)  # Monday, 19:00
        self.assertFalse(self.scheduler_service._should_run_schedule(mock_schedule, now))
        
        # Test with different day
        now = datetime(2023, 1, 7, 18, 0, 0)  # Saturday, 18:00
        self.assertFalse(self.scheduler_service._should_run_schedule(mock_schedule, now))
    
    @patch.object(SchedulerService, '_execute_schedule')
    def test_check_scheduled_tasks(self, mock_execute_schedule):
        """Test check scheduled tasks."""
        # Mock query
        mock_schedule = MagicMock()
        mock_schedule.is_active = True
        mock_schedule.days_of_week = [0, 1, 2, 3, 4]  # Monday to Friday
        mock_schedule.time_of_day = "18:00"
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_schedule]
        
        # Mock should_run_schedule
        self.scheduler_service._should_run_schedule = MagicMock(return_value=True)
        
        # Call method
        now = datetime(2023, 1, 2, 18, 0, 0)  # Monday, 18:00
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            self.scheduler_service._check_scheduled_tasks(now)
        )
        
        # Check mock calls
        mock_execute_schedule.assert_called_once_with(mock_schedule)

if __name__ == '__main__':
    unittest.main()

