from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Mentor(Base):
    __tablename__ = "Mentor"

    mentor_profile_id = Column(String(10), primary_key=True)  # MTR0001
    user_id = Column(String(10), ForeignKey("User.user_id"), nullable=False)
    expertise = Column(String(255))
    experience_years = Column(Integer)
    bio = Column(Text)
    linkedin_url = Column(String(255))