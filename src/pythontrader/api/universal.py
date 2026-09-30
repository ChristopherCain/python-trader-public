from fastapi import APIRouter

from pythontrader.autonomy.orchestrator import AutonomousTrader

router = APIRouter(prefix="/v1/universal", tags=["universal"])
brain = AutonomousTrader()


@router.get("/status")
def status():
    return brain.status()


@router.post("/scan")
def scan():
    return {"results": brain.scan_once(), "status": brain.status()}


@router.get("/universe")
def universe():
    return brain.registry.describe()


@router.get("/venues")
def venues():
    return {"synthetic": brain.venue.health()}
