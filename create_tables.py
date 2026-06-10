from database import engine, Base

# IMPORTANT: import all models so SQLAlchemy registers them
from models.mentor import MentorAssignment
from models.program import Program
from models.session import Session
from models.enrollment import Enrollment

Base.metadata.create_all(bind=engine)

print("Tables created successfully!")