from fastapi import HTTPException

from core.client import IntakeClient, LawyerClient, ServiceError

intake = IntakeClient()
lawyer = LawyerClient()


async def verify_ownership(case_id: str, lawyer_id: int) -> dict:
    try:
        case_data = await intake.get_case(case_id)
    except ServiceError as e:
        msg = e.detail if e.detail != "Service error" else "Case not found"
        raise HTTPException(status_code=e.status_code, detail=msg)
    except Exception:
        raise HTTPException(status_code=502, detail="Intake Service unavailable")
    if isinstance(case_data, dict) and "case" in case_data:
        case_lawyer_id = case_data["case"].get("lawyer_id")
        if case_lawyer_id is not None and case_lawyer_id != lawyer_id:
            raise HTTPException(status_code=403, detail="Access denied")
        return case_data
    raise HTTPException(status_code=404, detail="Case not found")
