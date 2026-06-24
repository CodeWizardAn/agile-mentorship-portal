from sqlalchemy import Column, String, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.sql import func
from database import Base

class Resource(Base):
    __tablename__ = "Resource"

    resource_id = Column(String(10), primary_key=True)  # RES0001

    # Scope: program-wide, or narrowed further to one session within that program.
    # program_id NULL  -> global resource (admin only)
    # program_id set, session_id NULL -> program-wide resource
    # program_id set, session_id set  -> session-specific resource
    program_id = Column(String(10), ForeignKey("Programs.program_id"), nullable=True)
    session_id = Column(String(10), ForeignKey("Session.session_id"), nullable=True)

    uploaded_by = Column(String(10), ForeignKey("User.user_id"), nullable=False)
    uploader_role = Column(String(10), nullable=False)  # admin / mentor

    title = Column(String(200), nullable=False)
    description = Column(Text)

    file_url = Column(String(255), nullable=False)
    file_type = Column(String(10))  # pdf, ppt, doc, excel, image, video, txt, file

    uploaded_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        CheckConstraint("uploader_role IN ('admin', 'mentor')", name="ck_resource_uploader_role"),
    )