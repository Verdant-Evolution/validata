import pydantic
from typing import List, Optional
from datetime import datetime


class Address(pydantic.BaseModel):
    street: str
    city: str
    zip_code: str


class Profile(pydantic.BaseModel):
    bio: Optional[str]
    website: Optional[str]
    age: int = 1

    @pydantic.field_validator("age")
    def age_must_be_positive(cls, v):
        if v < 0:
            raise ValueError("age must be positive")
        return v


class UserModel(pydantic.BaseModel):
    id: int
    email: Optional[str]
    is_active: bool
    signup_ts: Optional[datetime]
    scores: List[float]
    address: Address
    profile: Profile
    name: str = "myname"

    @pydantic.field_validator("email")
    def email_must_contain_at(cls, v):
        if v and "@" not in v:
            raise ValueError("email must contain '@'")
        return v
