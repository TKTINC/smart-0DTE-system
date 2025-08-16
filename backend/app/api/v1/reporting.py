from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List, Optional
from datetime import datetime, date, timedelta

from app.core.database import get_db, AsyncSessionLocal
from app.schemas.reporting import ReportResponse, ReportScheduleCreate, ReportScheduleResponse
from app.models.reporting import Report, ReportType, ReportSchedule
from app.services.odte_reporting_service import ODTEReportingService

router = APIRouter(
    prefix="/reporting",
    tags=["reporting"],
    responses={404: {"description": "Not found"}},
)

@router.get("/daily/{date}", response_model=ReportResponse)
async def get_daily_report(
    date: date,
    portfolio_id: int = 1,
    db: AsyncSession = Depends(get_db)
):
    """Get daily report for a specific date."""
    # Convert string date to datetime.date
    report_date = date
    
    # Check if report exists
    result = await db.execute(
        select(Report).where(
            Report.portfolio_id == portfolio_id,
            Report.report_type == ReportType.DAILY,
            Report.start_date == report_date,
            Report.end_date == report_date
        )
    )
    report = result.scalar_one_or_none()
    
    # If report doesn't exist, generate it
    if not report:
        reporting_service = ODTEReportingService(db)
        report_data = await reporting_service.generate_daily_report(report_date, portfolio_id)
        
        # Get the newly created report
        result = await db.execute(
            select(Report).where(
                Report.portfolio_id == portfolio_id,
                Report.report_type == ReportType.DAILY,
                Report.start_date == report_date,
                Report.end_date == report_date
            )
        )
        report = result.scalar_one_or_none()
        
        if not report:
            raise HTTPException(status_code=500, detail="Failed to generate report")
    
    return {
        "id": report.id,
        "portfolio_id": report.portfolio_id,
        "report_type": report.report_type,
        "start_date": report.start_date,
        "end_date": report.end_date,
        "title": report.title,
        "description": report.description,
        "report_data": report.report_data,
        "pdf_path": report.pdf_path,
        "created_at": report.created_at
    }

@router.get("/daily/{date}/pdf")
async def get_daily_report_pdf(
    date: date,
    portfolio_id: int = 1,
    db: AsyncSession = Depends(get_db)
):
    """Get PDF for daily report."""
    # Convert string date to datetime.date
    report_date = date
    
    # Check if report exists
    result = await db.execute(
        select(Report).where(
            Report.portfolio_id == portfolio_id,
            Report.report_type == ReportType.DAILY,
            Report.start_date == report_date,
            Report.end_date == report_date
        )
    )
    report = result.scalar_one_or_none()
    
    # If report doesn't exist or PDF doesn't exist, generate it
    if not report or not report.pdf_path:
        reporting_service = ODTEReportingService(db)
        report_data = await reporting_service.generate_daily_report(report_date, portfolio_id)
        
        # Get the newly created report
        result = await db.execute(
            select(Report).where(
                Report.portfolio_id == portfolio_id,
                Report.report_type == ReportType.DAILY,
                Report.start_date == report_date,
                Report.end_date == report_date
            )
        )
        report = result.scalar_one_or_none()
        
        if not report or not report.pdf_path:
            raise HTTPException(status_code=500, detail="Failed to generate report PDF")
    
    # Return PDF file
    return FileResponse(
        path=report.pdf_path,
        filename=f"daily_report_{report_date}.pdf",
        media_type="application/pdf"
    )

@router.get("/list", response_model=List[ReportResponse])
async def list_reports(
    report_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    portfolio_id: int = 1,
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List reports with optional filtering."""
    # Build query with filters
    query = select(Report).where(Report.portfolio_id == portfolio_id)
    
    if report_type:
        query = query.where(Report.report_type == report_type)
    
    if start_date:
        query = query.where(Report.start_date >= start_date)
    
    if end_date:
        query = query.where(Report.end_date <= end_date)
    
    # Order by date descending and apply pagination
    query = query.order_by(Report.start_date.desc()).offset(offset).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    reports = result.scalars().all()
    
    return reports

@router.post("/schedule", response_model=ReportScheduleResponse)
async def create_report_schedule(
    schedule: ReportScheduleCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new report schedule."""
    # Create new schedule
    db_schedule = ReportSchedule(
        user_id=schedule.user_id,
        report_type=schedule.report_type,
        is_active=schedule.is_active,
        time_of_day=schedule.time_of_day,
        days_of_week=schedule.days_of_week,
        email_delivery=schedule.email_delivery,
        notification_delivery=schedule.notification_delivery
    )
    
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    
    return db_schedule

@router.get("/schedule/{schedule_id}", response_model=ReportScheduleResponse)
async def get_report_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a report schedule by ID."""
    result = await db.execute(select(ReportSchedule).where(ReportSchedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Report schedule not found")
    
    return schedule

@router.delete("/schedule/{schedule_id}")
async def delete_report_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a report schedule."""
    result = await db.execute(select(ReportSchedule).where(ReportSchedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Report schedule not found")
    
    db.delete(schedule)
    db.commit()
    
    return {"message": "Report schedule deleted successfully"}

@router.post("/generate/daily")
async def generate_daily_report(
    background_tasks: BackgroundTasks,
    report_date: Optional[date] = None,
    portfolio_id: int = 1,
    db: AsyncSession = Depends(get_db)
):
    """Generate daily report in the background."""
    if report_date is None:
        report_date = datetime.utcnow().date()
    
    # Add task to background (pass only primitives, not session)
    background_tasks.add_task(_generate_daily_report_task, report_date, portfolio_id)
    
    return {"message": f"Daily report generation for {report_date} started in background"}

async def _generate_daily_report_task(report_date: date, portfolio_id: int):
    """Background task to generate daily report with fresh session."""
    async with AsyncSessionLocal() as db:
        try:
            reporting_service = ODTEReportingService(db)
            await reporting_service.generate_daily_report(report_date, portfolio_id)
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise

