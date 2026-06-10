from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from database import Base

class Announcement(Base):
    __tablename__ = "announcements"

    announcement_id = Column(String(10), primary_key=True)

    title = Column(String(200))

    message = Column(String(1000))

    created_by = Column(String(10))

    created_at = Column(DateTime, server_default=func.now())