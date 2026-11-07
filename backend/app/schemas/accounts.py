from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints
from typing import Annotated


Password = Annotated[str, StringConstraints(min_length=12, max_length=128)]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CollegeInput(InputModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    address: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]
    city: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    contact_email: EmailStr


class RepresentativeInput(InputModel):
    name: DisplayName
    email: EmailStr
    password: Password


class CollegeRegistrationInput(InputModel):
    college: CollegeInput
    representative: RepresentativeInput


class LoginInput(InputModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class CollegeUpdate(InputModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)] | None = None
    address: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)] | None = None
    city: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)] | None = None
    contact_email: EmailStr | None = None


class UserUpdate(InputModel):
    name: DisplayName | None = None
    email: EmailStr | None = None


class UserCreate(InputModel):
    name: DisplayName
    email: EmailStr
    password: Password


class UserStatusUpdate(InputModel):
    is_active: bool


class CollegeVerificationUpdate(InputModel):
    verification_status: str


