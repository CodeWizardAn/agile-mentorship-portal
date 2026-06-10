from sqlalchemy import Column, String, DateTime
from database import Base

class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(String(10), primary_key=True)

    title = Column(String(100))

    mentor_user_id = Column(String(10))

    program_id = Column(String(10))

    session_date = Column(DateTime)