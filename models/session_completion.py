from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from database import Base

class SessionCompletion(Base):
    __tablename__ = "SessionCompletion"

    completion_id = Column(String(10), primary_key=True)   # SC0001
    user_id       = Column(String(10), ForeignKey("User.user_id"), nullable=False)
    session_id    = Column(String(10), ForeignKey("Session.session_id"), nullable=False)
    program_id    = Column(String(10), ForeignKey("Programs.program_id"), nullable=False)
    completed     = Column(Boolean, default=False)
    completed_at  = Column(DateTime, server_default=func.now())