from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from database import Base

class VideoProgress(Base):
    __tablename__ = "VideoProgress"

    progress_id   = Column(String(10), primary_key=True)   # VP0001
    user_id       = Column(String(10), ForeignKey("User.user_id"), nullable=False)
    session_id    = Column(String(10), ForeignKey("Session.session_id"), nullable=False)
    # JSON string: list of [start, end] segments in seconds  e.g. "[[0,60],[120,180]]"
    watched_segments = Column(Text, default="[]")
    total_watched    = Column(Integer, default=0)           # unique seconds watched
    last_updated     = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "session_id", name="uq_user_session_progress"),
    )