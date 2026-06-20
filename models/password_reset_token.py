from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from database import Base

class PasswordResetToken(Base):
    __tablename__ = "PasswordResetToken"

    token       = Column(String(64), primary_key=True)
    user_id     = Column(String(10), ForeignKey("User.user_id"), nullable=False)
    is_used     = Column(Boolean, default=False)
    created_at  = Column(DateTime, server_default=func.now())
    expires_at  = Column(DateTime, nullable=False)