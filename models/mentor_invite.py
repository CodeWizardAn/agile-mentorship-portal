from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class MentorInvite(Base):
    __tablename__ = "MentorInvite"

    invite_id = Column(String(10), primary_key=True)
    invite_code = Column(String(20), unique=True, nullable=False)
    created_by = Column(String(10), ForeignKey("User.user_id"))
    used_by = Column(String(10), ForeignKey("User.user_id"))
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)