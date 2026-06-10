from sqlalchemy import Column, String, Integer, Text, Date, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from database import Base

class Program(Base):
    __tablename__ = "Programs"

    program_id = Column(String(10), primary_key=True)  # PRG0001
    title = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    duration_weeks = Column(Integer)
    start_date = Column(Date)
    end_date = Column(Date)
    created_by = Column(String(10), ForeignKey("User.user_id"))
    assigned_mentor = Column(String(10), ForeignKey("Mentor.mentor_profile_id"))
    status = Column(String(15), default="draft")
    created_at = Column(DateTime, server_default=func.now())