from sqlmodel import SQLModel, Field
from datetime import datetime, timedelta, timezone
from typing import Optional

time_now_jkt = lambda: datetime.now(tz=timezone(timedelta(hours=7)))

class YouTubeNote(SQLModel, table=True):
    __tablename__ = "youtube_note"

    id: Optional[int] = Field(default=None, primary_key=True)
    youtube_url: str
    title: Optional[str] = Field(default=None)
    transcript: str
    summary: str
    note: str
    created_at: datetime = Field(default_factory=time_now_jkt)
    updated_at: datetime = Field(default_factory=time_now_jkt, sa_column_kwargs={"onupdate": time_now_jkt})


