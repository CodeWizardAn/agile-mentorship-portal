from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class MentorCertificate(Base):
    __tablename__ = "MentorCertificate"

    cert_id = Column(String(10), primary_key=True)
    mentor_profile_id = Column(String(10), ForeignKey("Mentor.mentor_profile_id"), nullable=False)
    title = Column(String(200))
    file_url = Column(String(255))
    file_type = Column(String(10))
    uploaded_at = Column(DateTime, server_default=func.now())