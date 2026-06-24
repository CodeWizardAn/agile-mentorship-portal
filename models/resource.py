from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class Resource(Base):
    __tablename__ = "Resource"

    resource_id = Column(String(10), primary_key=True)          # RES0001
    title       = Column(String(200), nullable=False)
    description = Column(Text)
    file_url    = Column(String(500), nullable=False)
    file_type   = Column(String(20))                            # pdf, doc, ppt, image, video, excel, txt, file
    scope       = Column(String(10), default="global")          # global | program
    program_id  = Column(String(10), ForeignKey("Programs.program_id"), nullable=True)
    session_id  = Column(String(10), ForeignKey("Session.session_id"), nullable=True)
    uploaded_by = Column(String(10), ForeignKey("User.user_id"), nullable=False)
    uploaded_at = Column(DateTime, server_default=func.now())