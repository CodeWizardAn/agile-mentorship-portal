from sqlalchemy import Column, String
from database import Base

class Program(Base):
    __tablename__ = "programs"

    program_id = Column(String(10), primary_key=True)

    program_name = Column(String(100))

    course_code = Column(String(10), unique=True)

    description = Column(String(255))