import httpx
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from config import get_settings
from models import DataPipelineJob
from schemas import PipelineJobCreate
from cache import cache_service

settings = get_settings()


class AirflowClient:
    def __init__(self):
        self.base_url = settings.AIRFLOW_BASE_URL
        self.auth = (settings.AIRFLOW_USERNAME, settings.AIRFLOW_PASSWORD)

    async def trigger_dag(self, dag_id: str, conf: Optional[Dict] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns",
                json={"conf": conf or {}},
                auth=self.auth,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def get_dag_run_status(self, dag_id: str, run_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns/{run_id}",
                auth=self.auth,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def list_dags(self) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/dags",
                auth=self.auth,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()


class PipelineService:
    def __init__(self, db: Session):
        self.db = db
        self.airflow = AirflowClient()

    async def create_job(self, user_id: int, job_data: PipelineJobCreate) -> DataPipelineJob:
        job = DataPipelineJob(
            job_name=job_data.job_name,
            dag_id=job_data.dag_id,
            status="pending",
            created_by=user_id,
            created_at=datetime.utcnow()
        )

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        return job

    async def trigger_job(self, job_id: int, user_id: int) -> Optional[DataPipelineJob]:
        job = self.db.query(DataPipelineJob).filter(
            DataPipelineJob.id == job_id,
            DataPipelineJob.created_by == user_id
        ).first()

        if not job:
            return None

        try:
            result = await self.airflow.trigger_dag(job.dag_id, {"job_id": job_id})
            job.run_id = result.get("dag_run_id")
            job.status = "running"
            job.started_at = datetime.utcnow()
            self.db.commit()
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            self.db.commit()

        return job

    async def check_job_status(self, job_id: int, user_id: int) -> Optional[DataPipelineJob]:
        job = self.db.query(DataPipelineJob).filter(
            DataPipelineJob.id == job_id,
            DataPipelineJob.created_by == user_id
        ).first()

        if not job or not job.run_id:
            return job

        try:
            result = await self.airflow.get_dag_run_status(job.dag_id, job.run_id)
            airflow_status = result.get("state", "unknown")

            if airflow_status == "success":
                job.status = "completed"
                job.completed_at = datetime.utcnow()
            elif airflow_status == "failed":
                job.status = "failed"
                job.completed_at = datetime.utcnow()
            elif airflow_status == "running":
                job.status = "running"

            self.db.commit()
        except Exception:
            pass

        return job

    def get_jobs(self, user_id: int, skip: int = 0, limit: int = 50):
        return self.db.query(DataPipelineJob).filter(
            DataPipelineJob.created_by == user_id
        ).offset(skip).limit(limit).all()

    async def cancel_job(self, job_id: int, user_id: int) -> bool:
        job = self.db.query(DataPipelineJob).filter(
            DataPipelineJob.id == job_id,
            DataPipelineJob.created_by == user_id
        ).first()

        if not job:
            return False

        job.status = "cancelled"
        job.completed_at = datetime.utcnow()
        self.db.commit()

        return True


class DataSyncService:
    def __init__(self, db: Session):
        self.db = db

    async def sync_ad_platform_data(self, user_id: int, platform: str, date_range: tuple):
        lock_key = f"sync:{user_id}:{platform}"

        if not cache_service.acquire_lock(lock_key, timeout=300):
            raise Exception("Sync already in progress")

        try:
            await self._fetch_and_store_data(user_id, platform, date_range)
        except Exception as e:
            raise e

    async def _fetch_and_store_data(self, user_id: int, platform: str, date_range: tuple):
        pass

    def get_sync_status(self, user_id: int, platform: str) -> dict:
        cache_key = f"sync_status:{user_id}:{platform}"
        status = cache_service.get(cache_key)
        return status or {"status": "idle", "last_sync": None}
