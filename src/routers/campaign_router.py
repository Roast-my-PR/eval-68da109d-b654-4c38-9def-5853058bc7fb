from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from database import get_db
from models import User, CampaignStatus
from schemas import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    MetricsAggregation,
    BulkCampaignUpdate
)
from auth import get_current_active_user
from services.campaign_service import CampaignService
from cache import cache_service

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=List[CampaignResponse])
async def list_campaigns(
    status: Optional[CampaignStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = CampaignService(db)
    campaigns = service.get_campaigns(current_user.id, status, skip, limit)
    return campaigns


@router.post("", response_model=CampaignResponse)
async def create_campaign(
    campaign_data: CampaignCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = CampaignService(db)
    try:
        campaign = service.create_campaign(current_user.id, campaign_data)
        return campaign
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = CampaignService(db)
    campaign = service.get_campaign(campaign_id, current_user.id)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    return campaign


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    update_data: CampaignUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = CampaignService(db)
    campaign = service.update_campaign(campaign_id, current_user.id, update_data)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    return campaign


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = CampaignService(db)
    deleted = service.delete_campaign(campaign_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    return {"message": "Campaign deleted successfully"}


@router.post("/bulk-update", response_model=List[CampaignResponse])
async def bulk_update_campaigns(
    bulk_data: BulkCampaignUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = CampaignService(db)
    campaigns = service.bulk_update_campaigns(current_user.id, bulk_data)
    return campaigns


@router.get("/{campaign_id}/metrics", response_model=MetricsAggregation)
async def get_campaign_metrics(
    campaign_id: int,
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    cache_key = f"metrics:{campaign_id}:{start_date.date()}:{end_date.date()}"
    cached_metrics = cache_service.get(cache_key)

    if cached_metrics:
        return MetricsAggregation(**cached_metrics)

    service = CampaignService(db)
    metrics = service.calculate_aggregated_metrics(
        campaign_id, current_user.id, start_date, end_date
    )

    cache_service.set(cache_key, metrics, ttl=1800)

    return MetricsAggregation(**metrics)


@router.post("/{campaign_id}/sync")
async def sync_campaign(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = CampaignService(db)
    campaign = service.get_campaign(campaign_id, current_user.id)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    background_tasks.add_task(service.sync_campaign_data, campaign_id, current_user.id)

    return {"message": "Sync started", "campaign_id": campaign_id}


@router.get("/{campaign_id}/export")
async def export_campaign_data(
    campaign_id: int,
    format: str = Query("csv", regex="^(csv|json|xlsx)$"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = CampaignService(db)
    campaign = service.get_campaign(campaign_id, current_user.id)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)

    metrics = service.get_campaign_metrics(campaign_id, current_user.id, start_date, end_date)

    data = {
        "campaign": {
            "id": campaign.id,
            "name": campaign.name,
            "status": campaign.status.value,
            "budget": campaign.budget,
            "spent": campaign.spent
        },
        "metrics": [
            {
                "date": str(m.date),
                "impressions": m.impressions,
                "clicks": m.clicks,
                "conversions": m.conversions,
                "cost": m.cost,
                "revenue": m.revenue
            }
            for m in metrics
        ]
    }

    return data
