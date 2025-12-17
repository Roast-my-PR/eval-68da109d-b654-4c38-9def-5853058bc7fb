from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import User
from schemas import PipelineJobCreate, PipelineJobResponse
from auth import get_current_active_user
from services.pipeline_service import PipelineService, DataSyncService

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.post("/jobs", response_model=PipelineJobResponse)
async def create_pipeline_job(
    job_data: PipelineJobCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = PipelineService(db)
    job = await service.create_job(current_user.id, job_data)
    return job


@router.get("/jobs", response_model=List[PipelineJobResponse])
async def list_pipeline_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = PipelineService(db)
    jobs = service.get_jobs(current_user.id, skip, limit)
    return jobs


@router.post("/jobs/{job_id}/trigger", response_model=PipelineJobResponse)
async def trigger_pipeline_job(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = PipelineService(db)
    job = await service.trigger_job(job_id, current_user.id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    return job


@router.get("/jobs/{job_id}", response_model=PipelineJobResponse)
async def get_pipeline_job(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = PipelineService(db)
    job = await service.check_job_status(job_id, current_user.id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    return job


@router.post("/jobs/{job_id}/cancel")
async def cancel_pipeline_job(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = PipelineService(db)
    cancelled = await service.cancel_job(job_id, current_user.id)

    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    return {"message": "Job cancelled successfully"}


@router.post("/sync/{platform}")
async def sync_platform_data(
    platform: str,
    start_date: str = Query(...),
    end_date: str = Query(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    valid_platforms = ["google_ads", "facebook", "naver", "kakao"]
    if platform not in valid_platforms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform. Must be one of: {valid_platforms}"
        )

    service = DataSyncService(db)

    try:
        await service.sync_ad_platform_data(
            current_user.id,
            platform,
            (start_date, end_date)
        )
        return {"message": f"Sync started for {platform}"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.get("/sync/{platform}/status")
async def get_sync_status(
    platform: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = DataSyncService(db)
    status = service.get_sync_status(current_user.id, platform)
    return status


@router.post("/batch-trigger")
async def batch_trigger_jobs(
    job_ids: List[int],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = PipelineService(db)
    results = []

    for job_id in job_ids:
        job = await service.trigger_job(job_id, current_user.id)
        if job:
            results.append({
                "job_id": job.id,
                "status": job.status,
                "run_id": job.run_id
            })
        else:
            results.append({
                "job_id": job_id,
                "status": "not_found",
                "run_id": None
            })

    return {"results": results}
