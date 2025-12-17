from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: int
    exp: datetime


class AdAccountCreate(BaseModel):
    platform: str
    account_id: str
    account_name: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


class AdAccountResponse(BaseModel):
    id: int
    platform: str
    account_id: str
    account_name: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CampaignCreate(BaseModel):
    ad_account_id: int
    name: str = Field(..., min_length=1, max_length=255)
    budget: float = Field(default=0.0, ge=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[CampaignStatus] = None
    budget: Optional[float] = Field(None, ge=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class CampaignResponse(BaseModel):
    id: int
    name: str
    status: CampaignStatus
    budget: float
    spent: float
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MetricsResponse(BaseModel):
    campaign_id: int
    date: datetime
    impressions: int
    clicks: int
    conversions: int
    cost: float
    revenue: float
    ctr: float
    roas: float

    class Config:
        from_attributes = True


class MetricsAggregation(BaseModel):
    total_impressions: int
    total_clicks: int
    total_conversions: int
    total_cost: float
    total_revenue: float
    avg_ctr: float
    avg_roas: float


class PipelineJobCreate(BaseModel):
    job_name: str
    dag_id: str


class PipelineJobResponse(BaseModel):
    id: int
    job_name: str
    dag_id: str
    run_id: Optional[str]
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class BulkCampaignUpdate(BaseModel):
    campaign_ids: List[int]
    status: Optional[CampaignStatus] = None
    budget_adjustment: Optional[float] = None
