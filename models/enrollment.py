from sqlalchemy import Column, String
from database import Base

class Enrollment(Base):
    __tablename__ = "enrollments"

    enrollment_id = Column(String(20), primary_key=True)

    user_id = Column(String(10))

    program_id = Column(String(10))

    batch_no = Column(String(2))

    roll_no = Column(String(2))