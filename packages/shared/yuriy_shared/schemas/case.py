from pydantic import BaseModel


class PatchCasePinRequest(BaseModel):
    pinned: bool


class DeleteCaseResponse(BaseModel):
    case_id: str
    deleted: bool
