from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.sql import func
from database import Base

class Attendance(Base):
    __tablename__ = "Attendence"  # keeping original spelling

    attendance_id        = Column(String(10), primary_key=True)   # ATT0001
    session_id           = Column(String(10), ForeignKey("Session.session_id"), nullable=False)
    user_id              = Column(String(10), ForeignKey("User.user_id"), nullable=False)
    status               = Column(String(10), nullable=False, default="absent")  # present / absent
    marked_at            = Column(DateTime, server_default=func.now())

    # Live session auto-attendance fields
    join_intervals       = Column(Text, default="[]")   # JSON: [[join_iso, leave_iso], ...]
    total_minutes_present = Column(Integer, default=0)
    is_auto_marked       = Column(String(5), default="false")  # "true" / "false"