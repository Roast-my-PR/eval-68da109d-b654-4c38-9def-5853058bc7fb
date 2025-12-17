from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time

from config import get_settings
from database import engine, Base
from routers import auth_router, campaign_router, pipeline_router, admin_router
from cache import cache_service

settings = get_settings()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LEVER Xpert API",
    description="광고 운영 자동화 솔루션 API",
    version="1.0.0",
    debug=settings.DEBUG
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/admin"):
        return await call_next(request)

    client_ip = request.client.host
    endpoint = request.url.path

    rate_key = f"rate:{client_ip}:{endpoint}"
    current_count = cache_service.get_rate_limit_count(0, f"{client_ip}:{endpoint}")

    if current_count > 100:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"}
        )

    cache_service.increment_rate_limit(0, f"{client_ip}:{endpoint}", window=60)

    response = await call_next(request)
    return response


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
    )

    return response


@app.on_event("startup")
async def startup_event():
    logger.info("Starting LEVER Xpert API...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down LEVER Xpert API...")


app.include_router(auth_router)
app.include_router(campaign_router)
app.include_router(pipeline_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    return {"message": "LEVER Xpert API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "path": request.url.path
            }
        )

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
