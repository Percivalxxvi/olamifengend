from pydantic import BaseModel,EmailStr
from typing import Optional

class User(BaseModel):
    name:str
    email:EmailStr
    password:str
    role:str
    is_active:Optional[bool]=False

class Login(BaseModel):
    email:EmailStr
    password:str

class Post(BaseModel):
    title: str
    body: str
    author_id: str
    featured: Optional[bool] = False

