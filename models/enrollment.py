from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class Enrollment(Base):
    __tablename__ = "Enrollment"

    enrollment_id = Column(String(20), primary_key=True)  # e.g. 26PM1001
    user_id = Column(String(10), ForeignKey("User.user_id"), nullable=False)
    program_id = Column(String(10), ForeignKey("Programs.program_id"), nullable=False)
    enrollment_date = Column(DateTime, server_default=func.now())
    status = Column(String(15), default="active")