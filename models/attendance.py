from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class Attendance(Base):
    __tablename__ = "Attendence"  # keeping your original spelling

    attendance_id = Column(String(10), primary_key=True)  # ATT0001
    session_id = Column(String(10), ForeignKey("Session.session_id"), nullable=False)
    user_id = Column(String(10), ForeignKey("User.user_id"), nullable=False)
    status = Column(String(10), nullable=False)  # present / absent
    marked_at = Column(DateTime, server_default=func.now())