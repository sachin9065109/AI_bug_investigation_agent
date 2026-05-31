from fastapi import APIRouter
from api.schemas import BugRequest
from agent.orchestrator import run_agent

router = APIRouter()

@router.post("/analyze")
def analyze(req: BugRequest):
    return run_agent(req.title, req.body)
