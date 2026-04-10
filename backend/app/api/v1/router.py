from fastapi import APIRouter

from app.api.v1.endpoints import runs, artifacts, jobs, exports

api_router = APIRouter()

api_router.include_router(runs.router, prefix="/runs", tags=["runs"])
api_router.include_router(artifacts.router, prefix="/runs", tags=["artifacts"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(exports.router, prefix="/exports", tags=["exports"])
