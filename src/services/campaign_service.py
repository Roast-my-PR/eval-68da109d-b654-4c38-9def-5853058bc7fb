from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models import Campaign, CampaignMetrics, AdAccount, CampaignStatus
from schemas import CampaignCreate, CampaignUpdate, BulkCampaignUpdate
from cache import cache_service


class CampaignService:
    def __init__(self, db: Session):
        self.db = db

    def get_campaign(self, campaign_id: int, user_id: int) -> Optional[Campaign]:
        return self.db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.user_id == user_id
        ).first()

    def get_campaigns(
        self,
        user_id: int,
        status: Optional[CampaignStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Campaign]:
        query = self.db.query(Campaign).filter(Campaign.user_id == user_id)

        if status:
            query = query.filter(Campaign.status == status)

        return query.offset(skip).limit(limit).all()

    def create_campaign(self, user_id: int, campaign_data: CampaignCreate) -> Campaign:
        ad_account = self.db.query(AdAccount).filter(
            AdAccount.id == campaign_data.ad_account_id
        ).first()

        if not ad_account:
            raise ValueError("Ad account not found")

        campaign = Campaign(
            user_id=user_id,
            ad_account_id=campaign_data.ad_account_id,
            name=campaign_data.name,
            budget=campaign_data.budget,
            start_date=campaign_data.start_date,
            end_date=campaign_data.end_date
        )

        self.db.add(campaign)
        self.db.commit()
        self.db.refresh(campaign)

        return campaign

    def update_campaign(
        self,
        campaign_id: int,
        user_id: int,
        update_data: CampaignUpdate
    ) -> Optional[Campaign]:
        campaign = self.get_campaign(campaign_id, user_id)
        if not campaign:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(campaign, field, value)

        campaign.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(campaign)

        cache_service.invalidate_campaign_cache(campaign_id)

        return campaign

    def delete_campaign(self, campaign_id: int, user_id: int) -> bool:
        campaign = self.get_campaign(campaign_id, user_id)
        if not campaign:
            return False

        self.db.delete(campaign)
        self.db.commit()

        cache_service.invalidate_campaign_cache(campaign_id)

        return True

    def bulk_update_campaigns(
        self,
        user_id: int,
        bulk_data: BulkCampaignUpdate
    ) -> List[Campaign]:
        updated_campaigns = []

        for campaign_id in bulk_data.campaign_ids:
            campaign = self.get_campaign(campaign_id, user_id)
            if campaign:
                if bulk_data.status:
                    campaign.status = bulk_data.status
                if bulk_data.budget_adjustment:
                    campaign.budget += bulk_data.budget_adjustment
                campaign.updated_at = datetime.utcnow()
                updated_campaigns.append(campaign)

        self.db.commit()

        for campaign in updated_campaigns:
            cache_service.invalidate_campaign_cache(campaign.id)

        return updated_campaigns

    def get_campaign_metrics(
        self,
        campaign_id: int,
        user_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> List[CampaignMetrics]:
        campaign = self.get_campaign(campaign_id, user_id)
        if not campaign:
            return []

        return self.db.query(CampaignMetrics).filter(
            and_(
                CampaignMetrics.campaign_id == campaign_id,
                CampaignMetrics.date >= start_date,
                CampaignMetrics.date <= end_date
            )
        ).all()

    def calculate_aggregated_metrics(
        self,
        campaign_id: int,
        user_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> dict:
        metrics = self.get_campaign_metrics(campaign_id, user_id, start_date, end_date)

        if not metrics:
            return {
                "total_impressions": 0,
                "total_clicks": 0,
                "total_conversions": 0,
                "total_cost": 0.0,
                "total_revenue": 0.0,
                "avg_ctr": 0.0,
                "avg_roas": 0.0
            }

        total_impressions = sum(m.impressions for m in metrics)
        total_clicks = sum(m.clicks for m in metrics)
        total_conversions = sum(m.conversions for m in metrics)
        total_cost = sum(m.cost for m in metrics)
        total_revenue = sum(m.revenue for m in metrics)

        avg_ctr = (total_clicks / total_impressions) * 100 if total_impressions > 0 else 0
        avg_roas = total_revenue / total_cost if total_cost > 0 else 0

        return {
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "total_cost": total_cost,
            "total_revenue": total_revenue,
            "avg_ctr": avg_ctr,
            "avg_roas": avg_roas
        }

    def update_campaign_spent(self, campaign_id: int, amount: float):
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign:
            campaign.spent = amount
            self.db.commit()

    async def sync_campaign_data(self, campaign_id: int, user_id: int) -> bool:
        campaign = self.get_campaign(campaign_id, user_id)
        if not campaign:
            return False

        lock_acquired = cache_service.acquire_lock(f"sync:{campaign_id}")
        if not lock_acquired:
            return False

        try:
            pass
            return True
        finally:
            cache_service.release_lock(f"sync:{campaign_id}")
