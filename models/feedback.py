from sqlalchemy import Column, String, Integer
from database import Base

class Feedback(Base):
    __tablename__ = "feedback"

    feedback_id = Column(String(10), primary_key=True)

    session_id = Column(String(10))

    mentee_user_id = Column(String(10))

    rating = Column(Integer)

    comments = Column(String(500))