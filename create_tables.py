from database import engine, Base

from models.user import User
from models.mentor import Mentor
from models.mentor_invite import MentorInvite
from models.program import Program
from models.enrollment import Enrollment
from models.session import Session
from models.attendance import Attendance
from models.mentor_certificate import MentorCertificate
from models.video_progress import VideoProgress
from models.session_completion import SessionCompletion
from models.password_reset_token import PasswordResetToken
from models.resource import Resource
from models.email_otp import EmailOTP
from models.feedback import Feedback

Base.metadata.create_all(bind=engine)

print("Tables created successfully!")