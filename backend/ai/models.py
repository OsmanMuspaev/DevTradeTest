from pydantic import BaseModel, Field


class ChatCreateBody(BaseModel):
    name: str | None = Field(default=None, max_length=120)


class ChatRenameBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class MessageCreateBody(BaseModel):
    content: str = Field(min_length=1, max_length=50_000)


class StrategySubmitBody(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    language: str = Field(default="python", max_length=40)
    code: str = Field(min_length=1, max_length=200_000)