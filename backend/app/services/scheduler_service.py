import os
import logging
import asyncio
from datetime import datetime, time, timedelta
from typing import Dict, List, Any, Optional, Callable
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.reporting import ReportSchedule, ReportType
from app.services.odte_reporting_service import ODTEReportingService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

class SchedulerService:
    """Service for scheduling and executing tasks."""
    
    def __init__(self):
        """Initialize scheduler service."""
        self.tasks = {}
        self.running = False
        self.email_service = EmailService()
    
    async def start(self):
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        asyncio.create_task(self._run_scheduler())
        logger.info("Scheduler started")
    
    async def stop(self):
        """Stop the scheduler."""
        self.running = False
        logger.info("Scheduler stopped")
    
    async def _run_scheduler(self):
        """Run the scheduler loop."""
        while self.running:
            try:
                # Get current time
                now = datetime.utcnow()
                
                # Check for scheduled tasks
                await self._check_scheduled_tasks(now)
                
                # Sleep for 1 minute
                await asyncio.sleep(60)
            
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)
    
    async def _check_scheduled_tasks(self, now: datetime):
        """Check for scheduled tasks to execute."""
        # Get database session
        db = next(get_db())
        
        try:
            # Get active report schedules
            schedules = db.query(ReportSchedule).filter(ReportSchedule.is_active == True).all()
            
            for schedule in schedules:
                # Check if schedule should run now
                if self._should_run_schedule(schedule, now):
                    # Execute schedule
                    asyncio.create_task(self._execute_schedule(schedule))
        
        finally:
            db.close()
    
    def _should_run_schedule(self, schedule: ReportSchedule, now: datetime) -> bool:
        """Check if a schedule should run at the current time."""
        # Check day of week (0 = Monday, 6 = Sunday)
        if now.weekday() not in schedule.days_of_week:
            return False
        
        # Parse schedule time
        schedule_time = datetime.strptime(schedule.time_of_day, "%H:%M").time()
        
        # Check if current time matches schedule time (within 1 minute)
        current_time = now.time()
        
        # Calculate time difference in minutes
        time_diff = abs(
            (current_time.hour * 60 + current_time.minute) -
            (schedule_time.hour * 60 + schedule_time.minute)
        )
        
        # Return True if time difference is less than 1 minute
        return time_diff < 1
    
    async def _execute_schedule(self, schedule: ReportSchedule):
        """Execute a scheduled task."""
        logger.info(f"Executing schedule {schedule.id} for user {schedule.user_id}")
        
        # Get database session
        db = next(get_db())
        
        try:
            # Get user email
            from app.models.user import User
            user = db.query(User).filter(User.id == schedule.user_id).first()
            
            if not user:
                logger.error(f"User {schedule.user_id} not found")
                return
            
            # Execute based on report type
            if schedule.report_type == ReportType.DAILY:
                # Generate daily report
                reporting_service = ODTEReportingService(db)
                
                # Use yesterday's date for daily report
                report_date = datetime.utcnow().date() - timedelta(days=1)
                
                # Generate report
                report_data = await reporting_service.generate_daily_report(report_date, user.portfolio_id)
                
                # Get report
                from app.models.reporting import Report
                report = db.query(Report).filter(
                    Report.portfolio_id == user.portfolio_id,
                    Report.report_type == ReportType.DAILY,
                    Report.start_date == report_date,
                    Report.end_date == report_date
                ).first()
                
                if not report:
                    logger.error(f"Report not found for user {user.id} on {report_date}")
                    return
                
                # Send email if enabled
                if schedule.email_delivery and user.email:
                    await self.email_service.send_daily_report_email(
                        to_email=user.email,
                        report_date=report_date,
                        report_data=report.report_data,
                        pdf_path=report.pdf_path
                    )
                
                # Send notification if enabled
                if schedule.notification_delivery:
                    # TODO: Implement notification delivery
                    pass
            
            elif schedule.report_type == ReportType.WEEKLY:
                # TODO: Implement weekly report generation
                pass
            
            elif schedule.report_type == ReportType.MONTHLY:
                # TODO: Implement monthly report generation
                pass
            
            logger.info(f"Schedule {schedule.id} executed successfully")
        
        except Exception as e:
            logger.error(f"Error executing schedule {schedule.id}: {e}")
        
        finally:
            db.close()
    
    async def schedule_daily_report(
        self,
        user_id: int,
        time_of_day: str,
        days_of_week: List[int],
        email_delivery: bool = True,
        notification_delivery: bool = False
    ) -> Optional[ReportSchedule]:
        """Schedule a daily report."""
        # Get database session
        db = next(get_db())
        
        try:
            # Create schedule
            schedule = ReportSchedule(
                user_id=user_id,
                report_type=ReportType.DAILY,
                is_active=True,
                time_of_day=time_of_day,
                days_of_week=days_of_week,
                email_delivery=email_delivery,
                notification_delivery=notification_delivery
            )
            
            db.add(schedule)
            db.commit()
            db.refresh(schedule)
            
            logger.info(f"Daily report scheduled for user {user_id}")
            
            return schedule
        
        except Exception as e:
            logger.error(f"Error scheduling daily report: {e}")
            db.rollback()
            return None
        
        finally:
            db.close()
    
    async def schedule_weekly_report(
        self,
        user_id: int,
        time_of_day: str,
        day_of_week: int,
        email_delivery: bool = True,
        notification_delivery: bool = False
    ) -> Optional[ReportSchedule]:
        """Schedule a weekly report."""
        # Get database session
        db = next(get_db())
        
        try:
            # Create schedule
            schedule = ReportSchedule(
                user_id=user_id,
                report_type=ReportType.WEEKLY,
                is_active=True,
                time_of_day=time_of_day,
                days_of_week=[day_of_week],
                email_delivery=email_delivery,
                notification_delivery=notification_delivery
            )
            
            db.add(schedule)
            db.commit()
            db.refresh(schedule)
            
            logger.info(f"Weekly report scheduled for user {user_id}")
            
            return schedule
        
        except Exception as e:
            logger.error(f"Error scheduling weekly report: {e}")
            db.rollback()
            return None
        
        finally:
            db.close()
    
    async def schedule_monthly_report(
        self,
        user_id: int,
        time_of_day: str,
        day_of_month: int,
        email_delivery: bool = True,
        notification_delivery: bool = False
    ) -> Optional[ReportSchedule]:
        """Schedule a monthly report."""
        # Get database session
        db = next(get_db())
        
        try:
            # Create schedule
            schedule = ReportSchedule(
                user_id=user_id,
                report_type=ReportType.MONTHLY,
                is_active=True,
                time_of_day=time_of_day,
                days_of_week=[],  # Not used for monthly reports
                day_of_month=day_of_month,
                email_delivery=email_delivery,
                notification_delivery=notification_delivery
            )
            
            db.add(schedule)
            db.commit()
            db.refresh(schedule)
            
            logger.info(f"Monthly report scheduled for user {user_id}")
            
            return schedule
        
        except Exception as e:
            logger.error(f"Error scheduling monthly report: {e}")
            db.rollback()
            return None
        
        finally:
            db.close()

