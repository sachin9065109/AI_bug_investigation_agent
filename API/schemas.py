from pydantic import BaseModel

class BugRequest(BaseModel):
    title: str
    body: str


class BugResponse(BaseModel):
    severity: str
    root_cause: str
