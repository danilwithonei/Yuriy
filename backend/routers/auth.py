from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from auth import (
    create_token,
    get_current_lawyer,
    get_lawyer_by_email,
    hash_password,
    validate_email,
    verify_password,
)
from database import engine
from models import Lawyer
from schemas import AuthResponse, LawyerOut, LoginRequest, RegisterRequest

router = APIRouter()


@router.post("/auth/register")
async def register(request: RegisterRequest):
    email_err = validate_email(request.email)
    if email_err:
        raise HTTPException(status_code=400, detail=email_err)
    if len(request.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
    with Session(engine) as session:
        existing = get_lawyer_by_email(session, request.email)
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")
        lawyer_obj = Lawyer(
            email=request.email,
            name=request.name,
            password_hash=hash_password(request.password),
        )
        session.add(lawyer_obj)
        session.commit()
        session.refresh(lawyer_obj)
    token = create_token(lawyer_obj.id)
    return AuthResponse(token=token, lawyer=LawyerOut(id=lawyer_obj.id, email=lawyer_obj.email, name=lawyer_obj.name))


@router.post("/auth/login")
async def login(request: LoginRequest):
    with Session(engine) as session:
        lawyer_obj = get_lawyer_by_email(session, request.email)
        if not lawyer_obj or not verify_password(request.password, lawyer_obj.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(lawyer_obj.id)
    return AuthResponse(token=token, lawyer=LawyerOut(id=lawyer_obj.id, email=lawyer_obj.email, name=lawyer_obj.name))


@router.get("/auth/me")
async def me(lawyer_id: int = Depends(get_current_lawyer)):
    with Session(engine) as session:
        lawyer_obj = session.get(Lawyer, lawyer_id)
        if not lawyer_obj:
            raise HTTPException(status_code=404, detail="Lawyer not found")
        return LawyerOut(id=lawyer_obj.id, email=lawyer_obj.email, name=lawyer_obj.name)
