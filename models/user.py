from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "User"

    user_id = Column(String(10), primary_key=True)
    full_name = Column(String(100))
    email = Column(String(150), unique=True)
    password_hash = Column(String(255))
    role = Column(String(10))
    phone = Column(String(15))
    status = Column(String(10), default="active")
    created_at = Column(DateTime, server_default=func.now())
    profile_photo = Column(String(255))