from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.sql import func
from database import Base

class EmailOTP(Base):
    __tablename__ = "EmailOTP"

    otp_id     = Column(String(10), primary_key=True)       # OTP0001
    user_id    = Column(String(10), nullable=False)
    otp_code   = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used    = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())