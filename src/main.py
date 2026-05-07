from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, conint, constr
from typing import Optional
from itertools import count
from threading import Lock

app = FastAPI(title="Control Work 4 API")

class CustomExceptionA(Exception):
    def __init__(self, name: str):
        self.name = name

class CustomExceptionB(Exception):
    def __init__(self, resource_id: int):
        self.resource_id = resource_id

class ErrorResponse(BaseModel):
    error: str
    code: int
    detail: str

@app.exception_handler(CustomExceptionA)
async def custom_exception_a_handler(request: Request, exc: CustomExceptionA):
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(error="Condition Not Met", code=400, detail=f"Invalid name: {exc.name}").model_dump()
    )

@app.exception_handler(CustomExceptionB)
async def custom_exception_b_handler(request: Request, exc: CustomExceptionB):
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(error="Not Found", code=404, detail=f"Resource {exc.resource_id} not found").model_dump()
    )

@app.get("/error_a/{name}")
def trigger_error_a(name: str):
    if name == "bad":
        raise CustomExceptionA(name=name)
    return {"message": "Success"}

@app.get("/error_b/{resource_id}")
def trigger_error_b(resource_id: int):
    if resource_id == 0:
        raise CustomExceptionB(resource_id=resource_id)
    return {"message": "Success"}


class UserData(BaseModel):
    username: str
    age: int = Field(gt=18)
    email: EmailStr
    password: str = Field(min_length=8, max_length=16)
    phone: Optional[str] = 'Unknown'

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(error="Validation Error", code=422, detail=str(exc.errors())).model_dump()
    )

@app.post("/validate_user")
def validate_user(user: UserData):
    return {"message": "User validation successful", "user": user.model_dump()}


db: dict[int, dict] = {}
_id_seq = count(start=1)
_id_lock = Lock()

def next_user_id() -> int:
    with _id_lock:
        return next(_id_seq)

class UserIn(BaseModel):
    username: str
    age: int

class UserOut(BaseModel):
    id: int
    username: str
    age: int

@app.post("/users", response_model=UserOut, status_code=201)
def create_user(user: UserIn):
    user_id = next_user_id()
    db[user_id] = user.model_dump()
    return {"id": user_id, **db[user_id]}

@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int):
    if user_id not in db:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user_id, **db[user_id]}

@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int):
    if db.pop(user_id, None) is None:
        raise HTTPException(status_code=404, detail="User not found")
    return Response(status_code=204)
