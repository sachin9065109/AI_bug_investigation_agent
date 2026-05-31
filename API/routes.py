from fastapi import APIRouter
from agent.orchestrator import run_agent
from api.schemas import BugRequest

router = APIRouter()

@router.post("/analyze")
def analyze_bug(data: BugRequest):

    result = run_agent(
        title=data.title,
        body=data.body
    )

    return result
