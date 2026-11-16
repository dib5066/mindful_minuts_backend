from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


Billing = Literal["monthly", "yearly", "one-time"]


class PlanBase(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    price: int = Field(ge=0, description="Price in whole rupees")
    unit: str = Field(max_length=120)
    description: str
    features: list[str] = []
    href: str
    cta: str
    billing: Billing = "monthly"
    featured: bool = False
    position: int = 0


class PlanCreate(PlanBase):
    pass


class PlanUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    price: int | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=120)
    description: str | None = None
    features: list[str] | None = None
    href: str | None = None
    cta: str | None = None
    billing: Billing | None = None
    featured: bool | None = None
    position: int | None = None


class PlanOut(PlanBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    interest: str = Field(default="Personal Yoga", max_length=80)
    message: str = Field(default="", max_length=5000)


class ContactOut(ContactCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class TokenOut(BaseModel):
    token: str
    email: str


Mode = Literal["online", "offline"]
Period = Literal["hour", "week", "month"]


class PersonalPriceBase(BaseModel):
    mode: Mode
    period: Period
    price: int = Field(ge=0, description="Price in whole rupees")
    note: str = Field(default="", max_length=120)


class PersonalPriceCreate(PersonalPriceBase):
    pass


class PersonalPriceUpdate(BaseModel):
    mode: Mode | None = None
    period: Period | None = None
    price: int | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=120)


class PersonalPriceOut(PersonalPriceBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class GroupPriceBase(BaseModel):
    period: Period
    price: int = Field(ge=0, description="Price in whole rupees")
    note: str = Field(default="", max_length=120)


class GroupPriceCreate(GroupPriceBase):
    pass


class GroupPriceUpdate(BaseModel):
    period: Period | None = None
    price: int | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=120)


class GroupPriceOut(GroupPriceBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
