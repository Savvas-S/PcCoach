import re
from datetime import date, time
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator


class ServiceType(str, Enum):
    cleaning = "cleaning"
    repair = "repair"
    upgrade = "upgrade"
    diagnostics = "diagnostics"


class ServiceStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class ServiceBookingCreate(BaseModel):
    service_type: ServiceType
    description: str = Field(..., min_length=10, max_length=1000)
    preferred_date: date
    preferred_time: time
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=8, max_length=20)

    @field_validator("preferred_date")
    @classmethod
    def date_must_be_future(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("preferred_date must be today or in the future")
        return v

    @field_validator("phone")
    @classmethod
    def phone_format(cls, v: str) -> str:
        if not re.match(r"^\+?[\d\s\-]{8,20}$", v):
            raise ValueError("invalid phone number format")
        return v


class ServiceBooking(ServiceBookingCreate):
    id: int
    status: ServiceStatus = ServiceStatus.pending
