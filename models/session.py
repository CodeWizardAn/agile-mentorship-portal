from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.sql import func
from database import Base

class Session(Base):
    __tablename__ = "Session"

    session_id = Column(String(10), primary_key=True)  # SES0001
    program_id = Column(String(10), ForeignKey("Programs.program_id"), nullable=False)
    mentor_id = Column(String(10), ForeignKey("Mentor.mentor_profile_id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    session_type = Column(String(10), nullable=False)  # live / recorded
    scheduled_at = Column(DateTime)          # only for live
    meeting_link = Column(String(255))       # only for live
    video_url = Column(String(255))          # only for recorded
    duration_minutes = Column(Integer)
    status = Column(String(15), default="scheduled")  # scheduled/completed/cancelled
    created_at = Column(DateTime, server_default=func.now())