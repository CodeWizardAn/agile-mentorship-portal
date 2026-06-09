from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import DateTime
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)

    full_name = Column(String(100))

    email = Column(String(100), unique=True)

    password_hash = Column(String(255))

    role = Column(String(20))

    phone = Column(String(15))

    created_at = Column(DateTime, server_default=func.now())

    status = Column(String(20), default="ACTIVE")