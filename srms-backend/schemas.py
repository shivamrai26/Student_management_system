"""Request and response models for the API."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Role = Literal["admin", "teacher", "student"]
Status = Literal["draft", "submitted", "approved"]


class Text(BaseModel):
    """A string that must contain real text, not just whitespace.

    Field(min_length=1) alone accepts "   ", so strip before checking.
    """

    @field_validator("*", mode="before")
    @classmethod
    def _not_blank(cls, value):
        if isinstance(value, str) and not value.strip():
            raise ValueError("cannot be blank")
        return value


class LoginIn(Text):
    role: Role
    identifier: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=100)


class UserOut(BaseModel):
    id: str
    role: Role
    name: str


class RegisterIn(Text):
    """Student self-registration: the student picks their own roll and password."""

    roll: str = Field(min_length=2, max_length=20)
    name: str = Field(min_length=1, max_length=80)
    cls: str = Field(min_length=1, max_length=30)
    dob: str = Field(min_length=4, max_length=10)
    password: str = Field(min_length=6, max_length=100)


class TokenOut(BaseModel):
    token: str
    user: UserOut


class StudentIn(Text):
    name: str = Field(min_length=1, max_length=80)
    roll: str = Field(min_length=1, max_length=20)
    cls: str = Field(min_length=1, max_length=30)
    dob: str = Field(min_length=1, max_length=10)
    password: str = Field(default="stud123", min_length=1, max_length=100)


class SubjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    max_marks: int = Field(default=100, ge=1, le=1000)
    teacher_id: str | None = None


class AssignTeacherIn(BaseModel):
    teacher_id: str


class MarkEntry(BaseModel):
    student_id: str
    marks: int | None = Field(default=None, ge=0, le=1000)


class MarksSaveIn(BaseModel):
    subject_id: str
    action: Status = "draft"
    marks: list[MarkEntry]


class StatusIn(BaseModel):
    status: Status