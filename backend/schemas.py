from pydantic import BaseModel

class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class LawyerOut(BaseModel):
    id: int
    email: str
    name: str

class AuthResponse(BaseModel):
    token: str
    lawyer: LawyerOut
