from aiohttp import request
from fastapi import FastAPI, Request, Form, Depends, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import re
import secrets
from security import hash_password, verify_password, create_access_token, decode_access_token
from database import get_db
from models.user import User
from models.mentor_invite import MentorInvite
from models.mentor import Mentor
from models.program import Program
from models.enrollment import Enrollment
from models.session import Session as MentorSession
from models.attendance import Attendance
from fastapi import UploadFile, File
from cloudinary_config import upload_file
from models.mentor_certificate import MentorCertificate
from fastapi import HTTPException
from models.video_progress import VideoProgress
from models.session_completion import SessionCompletion
from pydantic import BaseModel
import json
from datetime import datetime, timezone
import threading
import time
from datetime import datetime, timezone, timedelta
from email_service import send_email, forgot_password_email, session_created_email, session_reminder_email
from models.password_reset_token import PasswordResetToken
from email_service import send_email, forgot_password_email, session_created_email, session_reminder_email, enrollment_confirmation_email
from models.feedback import Feedback
from models.password_reset_token import PasswordResetToken
from models.resource import Resource
from models.email_otp import EmailOTP
from email_service import   send_email, forgot_password_email, session_created_email, session_reminder_email, enrollment_confirmation_email, otp_verification_email
import random


BASE_URL = "http://localhost:8000"


app = FastAPI()

templates = Jinja2Templates(directory="templates")


# ── VALIDATIONS ───────────────────────────────────────────────────────────────

ALLOWED_DOMAINS = [
    "gmail.com", "yahoo.com", "outlook.com",
    "hotmail.com", "ac.in", "edu.in"
]

def validate_email(email: str) -> bool:
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
    if not re.match(pattern, email):
        return False
    domain = email.split("@")[1].lower()
    return any(domain == d or domain.endswith("." + d) for d in ALLOWED_DOMAINS)

def validate_password(password: str) -> bool:
    if len(password) < 6:
        return False
    if not password[0].isupper():
        return False
    return True

def generate_user_id(db: Session) -> str:
    year = str(datetime.now().year)[2:]
    last_user = db.query(func.max(User.user_id)).scalar()
    if last_user:
        last_serial = int(last_user[2:]) + 1
    else:
        last_serial = 1
    return f"{year}{last_serial:03d}"

def generate_mentor_id(db: Session) -> str:
    last_mentor = db.query(func.max(Mentor.mentor_profile_id)).scalar()
    if last_mentor:
        last_serial = int(last_mentor[3:]) + 1
    else:
        last_serial = 1
    return f"MTR{last_serial:04d}"

def generate_program_id(db: Session) -> str:
    last_program = db.query(func.max(Program.program_id)).scalar()
    if last_program:
        last_serial = int(last_program[3:]) + 1
    else:
        last_serial = 1
    return f"PRG{last_serial:04d}"

def generate_invite_id(db: Session) -> str:
    last_invite = db.query(func.max(MentorInvite.invite_id)).scalar()
    if last_invite:
        last_serial = int(last_invite[3:]) + 1
    else:
        last_serial = 1
    return f"INV{last_serial:04d}"

def generate_enrollment_id(db: Session, user_id: str, program_id: str) -> str:
    count = db.query(func.count(Enrollment.enrollment_id)).scalar() or 0
    serial = count + 1
    year = str(datetime.now().year)[2:]
    return f"ENR{year}{serial:05d}"

def generate_session_id(db: Session) -> str:
    last_session = db.query(func.max(MentorSession.session_id)).scalar()
    if last_session:
        last_serial = int(last_session[3:]) + 1
    else:
        last_serial = 1
    return f"SES{last_serial:04d}"

def generate_attendance_id(db: Session) -> str:
    last = db.query(func.max(Attendance.attendance_id)).scalar()
    if last:
        last_serial = int(last[3:]) + 1
    else:
        last_serial = 1
    return f"ATT{last_serial:04d}"

def generate_cert_id(db: Session) -> str:
    last = db.query(func.max(MentorCertificate.cert_id)).scalar()
    if last:
        last_serial = int(last[3:]) + 1
    else:
        last_serial = 1
    return f"CRT{last_serial:04d}"

def generate_resource_id(db: Session) -> str:
    last = db.query(func.max(Resource.resource_id)).scalar()
    if last:
        last_serial = int(last[3:]) + 1
    else:
        last_serial = 1
    return f"RES{last_serial:04d}"

def generate_otp_id(db: Session) -> str:
    last = db.query(func.max(EmailOTP.otp_id)).scalar()
    if last:
        last_serial = int(last[3:]) + 1
    else:
        last_serial = 1
    return f"OTP{last_serial:04d}"

# ── GET CURRENT USER FROM COOKIE ─────────────────────────────────────────────

def get_current_user(access_token: str = Cookie(None), db: Session = Depends(get_db)):
    if not access_token:
        return None
    payload = decode_access_token(access_token)
    if not payload:
        return None
    user = db.query(User).filter(User.user_id == payload.get("user_id")).first()
    return user


# ── PAGES ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="home.html")

@app.get("/signup/{role}", response_class=HTMLResponse)
def signup(request: Request, role: str):

    if role.lower() == "admin":
        return RedirectResponse(url="/login/admin", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="signup.html",
        context={"role": role}
    )

@app.get("/login/{role}", response_class=HTMLResponse)
def login(request: Request, role: str):
    return templates.TemplateResponse(
        request=request, name="login.html", context={"role": role}
    )

@app.get("/mentor-dashboard", response_class=HTMLResponse)
def mentor_dashboard(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user or current_user.role != "mentor":
        return RedirectResponse(url="/login/mentor", status_code=302)

    mentor = db.query(Mentor).filter(Mentor.user_id == current_user.user_id).first()
    sessions = []
    total_mentees = 0
    if mentor:
        sessions = db.query(MentorSession).filter(
            MentorSession.mentor_id == mentor.mentor_profile_id
        ).order_by(MentorSession.created_at.desc()).limit(4).all()

        programs = db.query(Program).filter(
            Program.assigned_mentor == mentor.mentor_profile_id
        ).all()
        program_ids = [p.program_id for p in programs]
        if program_ids:
            total_mentees = db.query(Enrollment).filter(
                Enrollment.program_id.in_(program_ids)
            ).count()

    from models.mentor_certificate import MentorCertificate
    stats = {
        "total_sessions": db.query(MentorSession).filter(
            MentorSession.mentor_id == mentor.mentor_profile_id
        ).count() if mentor else 0,
        "live_sessions": db.query(MentorSession).filter(
            MentorSession.mentor_id == mentor.mentor_profile_id,
            MentorSession.session_type == "live"
        ).count() if mentor else 0,
        "total_mentees": total_mentees,
        "total_certs": db.query(MentorCertificate).filter(
            MentorCertificate.mentor_profile_id == mentor.mentor_profile_id
        ).count() if mentor else 0,
    }

    pending_programs = db.query(Program).filter(
        Program.assigned_mentor == mentor.mentor_profile_id,
        Program.status == "pending"
    ).all() if mentor else []

    return templates.TemplateResponse(
        request=request, name="mentor_dashboard.html",
        context={"user": current_user, "stats": stats, "sessions": sessions, "pending_programs": pending_programs})
@app.get("/mentee-dashboard", response_class=HTMLResponse)
def mentee_dashboard(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user or current_user.role != "mentee":
        return RedirectResponse(url="/login/mentee", status_code=302)

    enrollments = db.query(Enrollment).filter(Enrollment.user_id == current_user.user_id).all()
    enrollment_data = []
    program_ids = []
    for e in enrollments:
        program = db.query(Program).filter(Program.program_id == e.program_id).first()
        enrollment_data.append({"program": program, "status": e.status, "enrollment_date": e.enrollment_date})
        program_ids.append(e.program_id)

    upcoming_sessions = db.query(MentorSession).filter(
        MentorSession.program_id.in_(program_ids),
        MentorSession.status == "scheduled"
    ).order_by(MentorSession.scheduled_at).limit(4).all() if program_ids else []

    recent_attendance = []
    att_records = db.query(Attendance).filter(
        Attendance.user_id == current_user.user_id
    ).order_by(Attendance.marked_at.desc()).limit(4).all()
    for a in att_records:
        session = db.query(MentorSession).filter(MentorSession.session_id == a.session_id).first()
        recent_attendance.append({"session": session, "status": a.status, "marked_at": a.marked_at})

    stats = {
        "total_enrollments": len(enrollments),
        "active_enrollments": sum(1 for e in enrollments if e.status == "active"),
        "sessions_attended": db.query(Attendance).filter(
            Attendance.user_id == current_user.user_id, Attendance.status == "present"
        ).count(),
        "upcoming_sessions": len(upcoming_sessions),
        "certificate_eligible": sum(1 for e in enrollments if e.status == "certificate_eligible"),
    }

    return templates.TemplateResponse(
        request=request, name="mentee_dashboard.html",
        context={"user": current_user, "stats": stats, "enrollments": enrollment_data,
                 "upcoming_sessions": upcoming_sessions, "recent_attendance": recent_attendance}
    )
# Replace the existing admin_dashboard route in main.py with this:

@app.get("/admin-dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user or current_user.role != "admin":
        return RedirectResponse(url="/login/admin", status_code=302)

    stats = {
        "total_programs":       db.query(Program).count(),
        "active_programs":      db.query(Program).filter(Program.status == "active").count(),
        "total_sessions":       db.query(MentorSession).count(),
        "live_sessions":        db.query(MentorSession).filter(MentorSession.session_type == "live").count(),
        "total_users":          db.query(User).filter(User.role != "admin").count(),
        "total_mentors":        db.query(User).filter(User.role == "mentor").count(),
        "total_enrollments":    db.query(Enrollment).count(),
        "certificate_eligible": db.query(Enrollment).filter(Enrollment.status == "certificate_eligible").count(),
    }

    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={"user": current_user, "request": request, "stats": stats}
    )


# ── SIGNUP ────────────────────────────────────────────────────────────────────

@app.post("/signup/{role}")
def create_user(
    role: str,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    invite_code: str = Form(None),
    db: Session = Depends(get_db)
):
    if role.lower() == "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin accounts cannot be created publicly."
        )
    if role == "mentor":
        if not invite_code:
            return templates.TemplateResponse("signup.html", {
                "request": {}, "role": role,
                "error": "Invite code is required for mentor signup"
            }, status_code=400)
        invite = db.query(MentorInvite).filter(
            MentorInvite.invite_code == invite_code.upper(),
            MentorInvite.is_used == False
        ).first()
        if not invite:
            return templates.TemplateResponse("signup.html", {
                "request": {}, "role": role,
                "error": "Invalid or already used invite code"
            }, status_code=400)

    if not validate_email(email):
        return templates.TemplateResponse("signup.html", {
            "request": {}, "role": role,
            "error": "Invalid email. Use a valid domain like gmail.com, yahoo.com, ac.in etc."
        }, status_code=400)

    if not validate_password(password):
        return templates.TemplateResponse("signup.html", {
            "request": {}, "role": role,
            "error": "Password must be at least 6 characters and start with a capital letter"
        }, status_code=400)

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return templates.TemplateResponse("signup.html", {
            "request": {}, "role": role,
            "error": "Email already registered"
        }, status_code=400)

    user_id = generate_user_id(db)
    user = User(
        user_id=user_id, full_name=full_name, email=email,
        password_hash=hash_password(password), role=role.lower(), status="unverified"
    )
    db.add(user)
    db.flush()

    if role == "mentor":
        mentor_profile_id = generate_mentor_id(db)
        mentor = Mentor(mentor_profile_id=mentor_profile_id, user_id=user_id)
        db.add(mentor)
        invite.is_used = True
        invite.used_by = user_id

    # create OTP
# create OTP
    try:
        otp_code = str(random.randint(100000, 999999))
        otp = EmailOTP(
            otp_id=generate_otp_id(db),
            user_id=user_id,
            otp_code=otp_code,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
        )
        db.add(otp)
        db.commit()
        print(f"DEBUG OTP created: {otp_code} for {user_id}")
    except Exception as e:
        print(f"DEBUG OTP ERROR: {e}")
        db.rollback()
        return RedirectResponse(url=f"/verify-email?user_id={user_id}&email={email}", status_code=302)

    # send OTP email
    html = otp_verification_email(full_name=full_name, otp_code=otp_code)
    send_email(email, "🔐 Verify your AgileMentor account", html)

    return RedirectResponse(url=f"/verify-email?user_id={user_id}&email={email}", status_code=302)
# ── LOGIN ─────────────────────────────────────────────────────────────────────

@app.post("/login/{role}")
def login_user(
    role: str,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    if not validate_email(email):
        return templates.TemplateResponse("login.html", {
            "request": {}, "role": role,
            "error": "Invalid email. Use a valid domain like gmail.com, yahoo.com, ac.in etc."
        }, status_code=400)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return templates.TemplateResponse("login.html", {
            "request": {}, "role": role, "error": "User not found"
        }, status_code=404)

    if user.role != role.lower():
        return templates.TemplateResponse("login.html", {
            "request": {}, "role": role, "error": "Invalid role for this account"
        }, status_code=403)

    if not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {
            "request": {}, "role": role, "error": "Invalid password"
        }, status_code=401)
        
    if user.status == "unverified":
        return templates.TemplateResponse("login.html", {
            "request": {}, "role": role,
            "error": "Please verify your email before logging in. Check your inbox for the OTP.",
            "unverified_user_id": user.user_id, "unverified_email": user.email
    }, status_code=403)

    token = create_access_token(data={
        "user_id": user.user_id, "role": user.role, "email": user.email
    })

    if user.role == "mentor":
        response = RedirectResponse(url="/mentor-dashboard", status_code=302)
    elif user.role == "mentee":
        response = RedirectResponse(url="/mentee-dashboard", status_code=302)
    elif user.role == "admin":
        response = RedirectResponse(url="/admin-dashboard", status_code=302)

    response.set_cookie(key="access_token", value=token, httponly=True)
    return response


# ── LOGOUT ────────────────────────────────────────────────────────────────────

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="access_token")
    return response


# ── GENERATE MENTOR INVITE (admin only) ───────────────────────────────────────

@app.post("/admin/generate-invite")
def generate_invite(
    admin_email: str = Form(...),
    db: Session = Depends(get_db)
):
    admin = db.query(User).filter(User.email == admin_email).first()
    if not admin or admin.role != "admin":
        return RedirectResponse(url="/admin-dashboard", status_code=302)

    invite_code = secrets.token_hex(6).upper()
    invite_id = generate_invite_id(db)

    invite = MentorInvite(
        invite_id=invite_id, invite_code=invite_code,
        created_by=admin.user_id, is_used=False
    )
    db.add(invite)
    db.commit()

    # redirect back to admin dashboard with invite code in query param
    return RedirectResponse(url=f"/admin-dashboard?invite_code={invite_code}", status_code=302)


# ── MENTOR PROFILE ────────────────────────────────────────────────────────────

@app.get("/mentor-profile", response_class=HTMLResponse)
def mentor_profile_page(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user or current_user.role != "mentor":
        return RedirectResponse(url="/login/mentor", status_code=302)
    mentor = db.query(Mentor).filter(Mentor.user_id == current_user.user_id).first()
    return templates.TemplateResponse(
        request=request,
        name="mentor_profile.html",
        context={"user": current_user, "mentor": mentor}
    )

@app.post("/mentor-profile/update")
def update_mentor_profile(
    expertise: str = Form(None),
    experience_years: int = Form(None),
    bio: str = Form(None),
    linkedin_url: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "mentor":
        return RedirectResponse(url="/login/mentor", status_code=302)

    mentor = db.query(Mentor).filter(Mentor.user_id == current_user.user_id).first()
    if not mentor:
        return RedirectResponse(url="/mentor-dashboard", status_code=302)

    if expertise: mentor.expertise = expertise
    if experience_years: mentor.experience_years = experience_years
    if bio: mentor.bio = bio
    if linkedin_url: mentor.linkedin_url = linkedin_url

    db.commit()
    return RedirectResponse(url="/mentor-profile", status_code=302)


# ── PROGRAMS ──────────────────────────────────────────────────────────────────

@app.get("/admin/programs", response_class=HTMLResponse)
def programs_page(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user or current_user.role != "admin":
        return RedirectResponse(url="/login/admin", status_code=302)
    programs = db.query(Program).all()
    return templates.TemplateResponse(
        request=request, name="programs.html",
        context={"user": current_user, "programs": programs}
    )

@app.post("/admin/programs/create")
def create_program(
    request: Request,
    title: str = Form(...),
    description: str = Form(None),
    category: str = Form(None),
    duration_weeks: int = Form(None),
    start_date: str = Form(None),
    end_date: str = Form(None),
    assigned_mentor: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    
    if not current_user or current_user.role != "admin":
        return RedirectResponse(url="/login/admin", status_code=302)
    if not title or not title[0].isupper():
        programs = db.query(Program).all()
        return templates.TemplateResponse("programs.html", {
            "request": request, "user": current_user, "programs": programs,
            "error": "Program title must start with a capital letter."
        })
    program_id = generate_program_id(db)
    program = Program(
        program_id=program_id, title=title, description=description,
        category=category, duration_weeks=duration_weeks,
        start_date=start_date, end_date=end_date,
        created_by=current_user.user_id,
        assigned_mentor=assigned_mentor if assigned_mentor else None,
        status="pending"
    )
    db.add(program)
    db.commit()
    return RedirectResponse(url="/admin/programs", status_code=302)

@app.post("/admin/programs/update/{program_id}")
def update_program(
    program_id: str,
    title: str = Form(None),
    description: str = Form(None),
    category: str = Form(None),
    duration_weeks: int = Form(None),
    start_date: str = Form(None),
    end_date: str = Form(None),
    assigned_mentor: str = Form(None),
    status: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "admin":
        return RedirectResponse(url="/login/admin", status_code=302)

    program = db.query(Program).filter(Program.program_id == program_id).first()
    if not program:
        return RedirectResponse(url="/admin/programs", status_code=302)

    if title: program.title = title
    if description: program.description = description
    if category: program.category = category
    if duration_weeks: program.duration_weeks = duration_weeks
    if start_date: program.start_date = start_date
    if end_date: program.end_date = end_date
    if assigned_mentor: program.assigned_mentor = assigned_mentor
    if status: program.status = status

    db.commit()
    return RedirectResponse(url="/admin/programs", status_code=302)

@app.post("/admin/programs/delete/{program_id}")
def delete_program(
    program_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "admin":
        return RedirectResponse(url="/login/admin", status_code=302)

    # Delete attendance for all sessions in this program
    program_sessions = db.query(MentorSession).filter(
        MentorSession.program_id == program_id
    ).all()
    for session in program_sessions:
        db.query(Attendance).filter(
            Attendance.session_id == session.session_id
        ).delete()
        db.query(VideoProgress).filter(
            VideoProgress.session_id == session.session_id
        ).delete()
        db.query(SessionCompletion).filter(
            SessionCompletion.session_id == session.session_id
        ).delete()

    # Delete sessions
    db.query(MentorSession).filter(
        MentorSession.program_id == program_id
    ).delete()

    # Delete enrollments
    db.query(Enrollment).filter(
        Enrollment.program_id == program_id
    ).delete()

    # Now delete the program
    program = db.query(Program).filter(Program.program_id == program_id).first()
    if program:
        db.delete(program)
    db.commit()
    return RedirectResponse(url="/admin/programs", status_code=302)

@app.get("/programs", response_class=HTMLResponse)
def view_programs(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user:
        return RedirectResponse(url="/login/mentee", status_code=302)
    programs = db.query(Program).filter(Program.status == "active").all()
    return templates.TemplateResponse(
        request=request, name="view_programs.html",
        context={"programs": programs, "user": current_user}
    )


# ── ENROLLMENT ────────────────────────────────────────────────────────────────


@app.post("/enroll/{program_id}")
def enroll_program(
    program_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "mentee":
        return RedirectResponse(url="/login/mentee", status_code=302)

    program = db.query(Program).filter(
        Program.program_id == program_id, Program.status == "active"
    ).first()
    if not program:
        return RedirectResponse(url="/programs", status_code=302)

    existing = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.user_id,
        Enrollment.program_id == program_id
    ).first()
    if existing:
        return RedirectResponse(url="/my-enrollments", status_code=302)

    enrollment_id = generate_enrollment_id(db, current_user.user_id, program_id)
    enrollment = Enrollment(
        enrollment_id=enrollment_id,
        user_id=current_user.user_id,
        program_id=program_id,
        status="active"
    )
    db.add(enrollment)
    db.commit()

    # Send enrollment confirmation email
    html = enrollment_confirmation_email(
        full_name=current_user.full_name,
        program_title=program.title,
        program_description=program.description,
        start_date=str(program.start_date) if program.start_date else None
    )
    threading.Thread(
        target=send_email,
        args=(current_user.email, f"Enrolled: {program.title}", html)
    ).start()

    return RedirectResponse(url="/my-enrollments", status_code=302)

    enrollment_id = generate_enrollment_id(db, current_user.user_id, program_id)
    enrollment = Enrollment(
        enrollment_id=enrollment_id,
        user_id=current_user.user_id,
        program_id=program_id,
        status="active"
    )
    db.add(enrollment)
    db.commit()
    return RedirectResponse(url="/my-enrollments", status_code=302)

@app.get("/my-enrollments", response_class=HTMLResponse)
def my_enrollments(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "mentee":
        return RedirectResponse(url="/login/mentee", status_code=302)

    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.user_id
    ).all()

    programs = []
    for e in enrollments:
        program = db.query(Program).filter(Program.program_id == e.program_id).first()
        programs.append({
            "enrollment_id": e.enrollment_id,
            "program": program,
            "status": e.status,
            "enrollment_date": e.enrollment_date
        })

    return templates.TemplateResponse(
        request=request, name="my_enrollments.html",
        context={"enrollments": programs, "user": current_user}
    )


# ── ADMIN USER MANAGEMENT ─────────────────────────────────────────────────────

@app.get("/admin/users", response_class=HTMLResponse)
def manage_users(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user or current_user.role != "admin":
        return RedirectResponse(url="/login/admin", status_code=302)
    users = db.query(User).filter(User.role != "admin").all()
    return templates.TemplateResponse(
        request=request, name="manage_users.html",
        context={"users": users, "user": current_user}
    )

@app.post("/admin/users/delete/{user_id}")
def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "admin":
        return RedirectResponse(url="/login/admin", status_code=302)

    mentor = db.query(Mentor).filter(Mentor.user_id == user_id).first()
    if mentor:
        mentor_sessions = db.query(MentorSession).filter(
            MentorSession.mentor_id == mentor.mentor_profile_id
        ).all()
        for s in mentor_sessions:
            db.query(Attendance).filter(Attendance.session_id == s.session_id).delete()
            db.query(VideoProgress).filter(VideoProgress.session_id == s.session_id).delete()
            db.query(SessionCompletion).filter(SessionCompletion.session_id == s.session_id).delete()
            db.query(Feedback).filter(Feedback.session_id == s.session_id).update(
                {"session_id": None}, synchronize_session=False
            )
        db.query(MentorSession).filter(
            MentorSession.mentor_id == mentor.mentor_profile_id
        ).delete()
        db.query(Program).filter(
            Program.assigned_mentor == mentor.mentor_profile_id
        ).update({"assigned_mentor": None}, synchronize_session=False)
        db.delete(mentor)

    # Mentee cleanup
    db.query(Attendance).filter(Attendance.user_id == user_id).delete()
    db.query(VideoProgress).filter(VideoProgress.user_id == user_id).delete()
    db.query(SessionCompletion).filter(SessionCompletion.user_id == user_id).delete()
    db.query(Feedback).filter(Feedback.mentee_user_id == user_id).update(
    {"mentee_user_id": None}, synchronize_session=False
)
    db.query(Enrollment).filter(Enrollment.user_id == user_id).delete()
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).delete()

    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        db.delete(user)
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=302)


# ── SESSIONS ──────────────────────────────────────────────────────────────────

@app.get("/admin/sessions", response_class=HTMLResponse)
def admin_sessions_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "admin":
        return RedirectResponse(url="/login/admin", status_code=302)
    sessions = db.query(MentorSession).all()
    programs = db.query(Program).all()
    mentors = db.query(Mentor, User).join(User, Mentor.user_id == User.user_id).all()
    return templates.TemplateResponse(
        request=request, name="admin_sessions.html",
        context={"user": current_user, "sessions": sessions, "programs": programs, "mentors": mentors}
    )

@app.post("/admin/sessions/create")
def admin_create_session(
    program_id: str = Form(...),
    mentor_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(None),
    session_type: str = Form(...),
    scheduled_at: str = Form(None),
    meeting_link: str = Form(None),
    video_url: str = Form(None),
    duration_minutes: int = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "admin":
        return RedirectResponse(url="/login/admin", status_code=302)
 
    session_id = generate_session_id(db)
    session = MentorSession(
        session_id=session_id, program_id=program_id, mentor_id=mentor_id,
        title=title, description=description, session_type=session_type,
        scheduled_at=scheduled_at if scheduled_at else None,
        meeting_link=meeting_link if meeting_link else None,
        video_url=video_url if video_url else None,
        duration_minutes=duration_minutes, status="scheduled"
    )
    db.add(session)
    db.commit()
 
    # ── Notify enrolled mentees ───────────────────────────────────────────────
    enrollments = db.query(Enrollment).filter(Enrollment.program_id == program_id).all()
    program = db.query(Program).filter(Program.program_id == program_id).first()
    program_title = program.title if program else program_id
 
    mentee_list = []
    for e in enrollments:
        mentee = db.query(User).filter(User.user_id == e.user_id).first()
        if mentee:
            mentee_list.append((mentee.full_name, mentee.email))
            html = session_created_email(
                full_name=mentee.full_name,
                session_title=title,
                session_type=session_type,
                program_title=program_title,
                scheduled_at=scheduled_at if scheduled_at else None,
                meeting_link=meeting_link,
                video_url=video_url
            )
            threading.Thread(
                target=send_email,
                args=(mentee.email, f"New Session Added: {title}", html)
            ).start()
 
    # ── Schedule reminder for live sessions ───────────────────────────────────
    if session_type == "live" and scheduled_at and meeting_link and mentee_list:
        try:
            # Parse the datetime — FastAPI form sends it as "YYYY-MM-DDTHH:MM"
            scheduled_dt = datetime.fromisoformat(scheduled_at)
            if scheduled_dt.tzinfo is None:
                scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
 
            schedule_session_reminder(
                session_id=session_id,
                session_title=title,
                program_title=program_title,
                scheduled_at_dt=scheduled_dt,
                meeting_link=meeting_link,
                mentee_list=mentee_list,
                minutes_before=30
            )
        except Exception as e:
            print(f"[REMINDER] Failed to schedule reminder: {e}")
 
    return RedirectResponse(url="/admin/sessions", status_code=302)
 

 


@app.post("/admin/sessions/update/{session_id}")
def admin_update_session(
    session_id: str,
    title: str = Form(None),
    description: str = Form(None),
    scheduled_at: str = Form(None),
    meeting_link: str = Form(None),
    video_url: str = Form(None),
    duration_minutes: int = Form(None),
    status: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "admin":
        return RedirectResponse(url="/login/admin", status_code=302)

    session = db.query(MentorSession).filter(MentorSession.session_id == session_id).first()
    if not session:
        return RedirectResponse(url="/admin/sessions", status_code=302)

    if title: session.title = title
    if description: session.description = description
    if scheduled_at: session.scheduled_at = scheduled_at
    if meeting_link: session.meeting_link = meeting_link
    if video_url: session.video_url = video_url
    if duration_minutes: session.duration_minutes = duration_minutes
    if status: session.status = status

    db.commit()
    return RedirectResponse(url="/admin/sessions", status_code=302)

@app.post("/admin/sessions/delete/{session_id}")
def admin_delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "admin":
        return RedirectResponse(url="/login/admin", status_code=302)

    db.query(Attendance).filter(Attendance.session_id == session_id).delete()
    db.query(VideoProgress).filter(VideoProgress.session_id == session_id).delete()
    db.query(SessionCompletion).filter(SessionCompletion.session_id == session_id).delete()
    # Feedback uses nullable FK so just nullify
    db.query(Feedback).filter(Feedback.session_id == session_id).update(
        {"session_id": None}, synchronize_session=False
    )

    session = db.query(MentorSession).filter(MentorSession.session_id == session_id).first()
    if session:
        db.delete(session)
    db.commit()
    return RedirectResponse(url="/admin/sessions", status_code=302)


# ── MENTOR SESSIONS ───────────────────────────────────────────────────────────

@app.get("/mentor/sessions", response_class=HTMLResponse)
def mentor_sessions_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "mentor":
        return RedirectResponse(url="/login/mentor", status_code=302)

    mentor = db.query(Mentor).filter(Mentor.user_id == current_user.user_id).first()
    if not mentor:
        return RedirectResponse(url="/mentor-dashboard", status_code=302)

    sessions = db.query(MentorSession).filter(MentorSession.mentor_id == mentor.mentor_profile_id).all()
    return templates.TemplateResponse(
        request=request, name="mentor_sessions.html",
        context={"user": current_user, "sessions": sessions, "mentor": mentor}
    )

@app.post("/mentor/sessions/create")
def mentor_create_session(
    program_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(None),
    session_type: str = Form(...),
    scheduled_at: str = Form(None),
    meeting_link: str = Form(None),
    video_url: str = Form(None),
    duration_minutes: int = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "mentor":
        return RedirectResponse(url="/login/mentor", status_code=302)
 
    mentor = db.query(Mentor).filter(Mentor.user_id == current_user.user_id).first()
    program = db.query(Program).filter(
        Program.program_id == program_id,
        Program.assigned_mentor == mentor.mentor_profile_id
    ).first()
    if not program:
        return RedirectResponse(url="/mentor/sessions", status_code=302)
 
    session_id = generate_session_id(db)
    session = MentorSession(
        session_id=session_id, program_id=program_id,
        mentor_id=mentor.mentor_profile_id, title=title, description=description,
        session_type=session_type,
        scheduled_at=scheduled_at if scheduled_at else None,
        meeting_link=meeting_link if meeting_link else None,
        video_url=video_url if video_url else None,
        duration_minutes=duration_minutes, status="scheduled"
    )
    db.add(session)
    db.commit()
 
    # ── Notify enrolled mentees ───────────────────────────────────────────────
    enrollments = db.query(Enrollment).filter(Enrollment.program_id == program_id).all()
 
    mentee_list = []
    for e in enrollments:
        mentee = db.query(User).filter(User.user_id == e.user_id).first()
        if mentee:
            mentee_list.append((mentee.full_name, mentee.email))
            html = session_created_email(
                full_name=mentee.full_name,
                session_title=title,
                session_type=session_type,
                program_title=program.title,
                scheduled_at=scheduled_at if scheduled_at else None,
                meeting_link=meeting_link,
                video_url=video_url
            )
            threading.Thread(
                target=send_email,
                args=(mentee.email, f"New Session Added: {title}", html)
            ).start()
 
    # ── Schedule reminder for live sessions ───────────────────────────────────
    if session_type == "live" and scheduled_at and meeting_link and mentee_list:
        try:
            scheduled_dt = datetime.fromisoformat(scheduled_at)
            if scheduled_dt.tzinfo is None:
                scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
 
            schedule_session_reminder(
                session_id=session_id,
                session_title=title,
                program_title=program.title,
                scheduled_at_dt=scheduled_dt,
                meeting_link=meeting_link,
                mentee_list=mentee_list,
                minutes_before=30
            )
        except Exception as e:
            print(f"[REMINDER] Failed to schedule reminder: {e}")
 
    return RedirectResponse(url="/mentor/sessions", status_code=302)

@app.post("/mentor/sessions/update/{session_id}")
def mentor_update_session(
    session_id: str,
    title: str = Form(None),
    description: str = Form(None),
    scheduled_at: str = Form(None),
    meeting_link: str = Form(None),
    video_url: str = Form(None),
    duration_minutes: int = Form(None),
    status: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "mentor":
        return RedirectResponse(url="/login/mentor", status_code=302)

    mentor = db.query(Mentor).filter(Mentor.user_id == current_user.user_id).first()
    session = db.query(MentorSession).filter(
        MentorSession.session_id == session_id,
        MentorSession.mentor_id == mentor.mentor_profile_id
    ).first()
    if not session:
        return RedirectResponse(url="/mentor/sessions", status_code=302)

    if title: session.title = title
    if description: session.description = description
    if scheduled_at: session.scheduled_at = scheduled_at
    if meeting_link: session.meeting_link = meeting_link
    if video_url: session.video_url = video_url
    if duration_minutes: session.duration_minutes = duration_minutes
    if status: session.status = status

    db.commit()
    return RedirectResponse(url="/mentor/sessions", status_code=302)

@app.post("/mentor/sessions/delete/{session_id}")
def mentor_delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "mentor":
        return RedirectResponse(url="/login/mentor", status_code=302)

    mentor = db.query(Mentor).filter(Mentor.user_id == current_user.user_id).first()
    session = db.query(MentorSession).filter(
        MentorSession.session_id == session_id,
        MentorSession.mentor_id == mentor.mentor_profile_id
    ).first()
    if session:
        db.delete(session)
        db.commit()
    return RedirectResponse(url="/mentor/sessions", status_code=302)


# ── MENTEE SESSIONS ───────────────────────────────────────────────────────────

@app.get("/my-sessions", response_class=HTMLResponse)
def mentee_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "mentee":
        return RedirectResponse(url="/login/mentee", status_code=302)

    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.user_id
    ).all()
    program_ids = [e.program_id for e in enrollments]
    sessions = db.query(MentorSession).filter(
        MentorSession.program_id.in_(program_ids)
    ).all()

    return templates.TemplateResponse(
        request=request, name="my_sessions.html",
        context={"user": current_user, "sessions": sessions}
    )


# ── ATTENDANCE ────────────────────────────────────────────────────────────────

@app.get("/admin/attendance", response_class=HTMLResponse)
def admin_attendance_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "admin":
        return RedirectResponse(url="/login/admin", status_code=302)
    sessions = db.query(MentorSession).all()
    return templates.TemplateResponse(
        request=request, name="admin_attendance.html",
        context={"user": current_user, "sessions": sessions}
    )

@app.get("/attendance/{session_id}", response_class=HTMLResponse)
def view_session_attendance(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role not in ["admin", "mentor"]:
        return RedirectResponse(url="/login/admin", status_code=302)

    session = db.query(MentorSession).filter(MentorSession.session_id == session_id).first()
    if not session:
        return RedirectResponse(url="/admin/attendance", status_code=302)

    enrollments = db.query(Enrollment).filter(
        Enrollment.program_id == session.program_id
    ).all()

    mentees = []
    for e in enrollments:
        user = db.query(User).filter(User.user_id == e.user_id).first()
        attendance = db.query(Attendance).filter(
            Attendance.session_id == session_id,
            Attendance.user_id == e.user_id
        ).first()
        mentees.append({"user": user, "attendance": attendance})

    return templates.TemplateResponse(
        request=request, name="mark_attendance.html",
        context={"user": current_user, "session": session, "mentees": mentees}
    )

@app.post("/attendance/mark/{session_id}")
def mark_attendance(
    session_id: str,
    user_id: str = Form(...),
    status: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role not in ["admin", "mentor"]:
        return RedirectResponse(url="/login/admin", status_code=302)

    existing = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.user_id == user_id
    ).first()

    if existing:
        existing.status = status
    else:
        attendance_id = generate_attendance_id(db)
        attendance = Attendance(
            attendance_id=attendance_id,
            session_id=session_id,
            user_id=user_id,
            status=status
        )
        db.add(attendance)

    db.commit()
    return RedirectResponse(url=f"/attendance/{session_id}", status_code=302)

@app.get("/my-attendance", response_class=HTMLResponse)
def my_attendance(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "mentee":
        return RedirectResponse(url="/login/mentee", status_code=302)

    attendance_records = db.query(Attendance).filter(
        Attendance.user_id == current_user.user_id
    ).all()

    records = []
    for a in attendance_records:
        session = db.query(MentorSession).filter(
            MentorSession.session_id == a.session_id
        ).first()
        records.append({"session": session, "status": a.status, "marked_at": a.marked_at})

    return templates.TemplateResponse(
        request=request, name="my_attendance.html",
        context={"user": current_user, "records": records}
    )


# ── PROFILE PHOTO UPLOAD ──────────────────────────────────────────────────────

@app.post("/upload/profile-photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login/mentee", status_code=302)

    contents = await file.read()
    url = upload_file(contents, folder="agilementor/profiles", resource_type="image")
    current_user.profile_photo = url
    db.commit()
    return RedirectResponse(url="/mentor-profile", status_code=302)


# ── MENTOR CERTIFICATE ────────────────────────────────────────────────────────

@app.post("/mentor/upload-certificate")
async def upload_certificate(
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "mentor":
        return RedirectResponse(url="/login/mentor", status_code=302)

    mentor = db.query(Mentor).filter(Mentor.user_id == current_user.user_id).first()
    if not mentor:
        return RedirectResponse(url="/mentor-dashboard", status_code=302)

    contents = await file.read()
    filename = file.filename.lower()
    if filename.endswith(".pdf"):
        file_type = "pdf"
        resource_type = "raw"
    else:
        file_type = "image"
        resource_type = "image"

    url = upload_file(contents, folder="agilementor/certificates", resource_type=resource_type)
    cert_id = generate_cert_id(db)
    cert = MentorCertificate(
        cert_id=cert_id, mentor_profile_id=mentor.mentor_profile_id,
        title=title, file_url=url, file_type=file_type
    )
    db.add(cert)
    db.commit()
    return RedirectResponse(url="/mentor/certificates", status_code=302)

@app.get("/mentor/certificates", response_class=HTMLResponse)
def mentor_certificates_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "mentor":
        return RedirectResponse(url="/login/mentor", status_code=302)

    mentor = db.query(Mentor).filter(Mentor.user_id == current_user.user_id).first()
    certs = db.query(MentorCertificate).filter(
        MentorCertificate.mentor_profile_id == mentor.mentor_profile_id
    ).all()

    return templates.TemplateResponse(
        request=request, name="mentor_certificates.html",
        context={"user": current_user, "certs": certs, "mentor": mentor}
    )

@app.post("/mentor/delete-certificate/{cert_id}")
def delete_certificate(
    cert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "mentor":
        return RedirectResponse(url="/login/mentor", status_code=302)

    cert = db.query(MentorCertificate).filter(MentorCertificate.cert_id == cert_id).first()
    if cert:
        db.delete(cert)
        db.commit()
    return RedirectResponse(url="/mentor/certificates", status_code=302)

# ── VIDEO PROGRESS TRACKING ───────────────────────────────────────────────────


class SegmentPayload(BaseModel):
    session_id: str
    start: float
    end: float

def generate_progress_id(db):
    from models.video_progress import VideoProgress
    last = db.query(func.max(VideoProgress.progress_id)).scalar()
    if last:
        last_serial = int(last[2:]) + 1
    else:
        last_serial = 1
    return f"VP{last_serial:04d}"

def generate_completion_id(db):
    from models.session_completion import SessionCompletion
    last = db.query(func.max(SessionCompletion.completion_id)).scalar()
    if last:
        last_serial = int(last[2:]) + 1
    else:
        last_serial = 1
    return f"SC{last_serial:04d}"

def merge_segments(segments: list) -> int:
    """Merge overlapping [start, end] segments and return total unique seconds watched."""
    if not segments:
        return 0
    segments.sort(key=lambda x: x[0])
    merged = [segments[0]]
    for start, end in segments[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return int(sum(end - start for start, end in merged))


@app.post("/api/video/progress")
def update_video_progress(
    payload: SegmentPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Called every 5 seconds from frontend with the current watched segment.
    Merges segments and checks if 95% of video is watched.
    """
    if not current_user or current_user.role != "mentee":
        raise HTTPException(status_code=403, detail="Mentees only")

    session = db.query(MentorSession).filter(
        MentorSession.session_id == payload.session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify mentee is enrolled in this program
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.user_id,
        Enrollment.program_id == session.program_id
    ).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="Not enrolled in this program")

    # Get or create progress record
    progress = db.query(VideoProgress).filter(
        VideoProgress.user_id == current_user.user_id,
        VideoProgress.session_id == payload.session_id
    ).first()

    if not progress:
        progress_id = generate_progress_id(db)
        progress = VideoProgress(
            progress_id=progress_id,
            user_id=current_user.user_id,
            session_id=payload.session_id,
            watched_segments="[]",
            total_watched=0
        )
        db.add(progress)
        db.flush()

    # Merge new segment with existing ones
    existing = json.loads(progress.watched_segments or "[]")
    existing.append([round(payload.start, 2), round(payload.end, 2)])
    merged_unique_seconds = merge_segments(existing)

    progress.watched_segments = json.dumps(existing)
    progress.total_watched = merged_unique_seconds

    # Check if 95% of video watched (anti-skip: based on unique segments, not seek position)
    duration_seconds = (session.duration_minutes or 0) * 60
    is_complete = duration_seconds > 0 and merged_unique_seconds >= duration_seconds * 0.95

    db.commit()

    # If complete, mark session as completed for this mentee
    if is_complete:
        existing_completion = db.query(SessionCompletion).filter(
            SessionCompletion.user_id == current_user.user_id,
            SessionCompletion.session_id == payload.session_id
        ).first()

        if not existing_completion:
            completion_id = generate_completion_id(db)
            completion = SessionCompletion(
                completion_id=completion_id,
                user_id=current_user.user_id,
                session_id=payload.session_id,
                program_id=session.program_id,
                completed=True
            )
            db.add(completion)
            db.commit()

            # Check if ALL recorded sessions in this program are now complete
            all_recorded_sessions = db.query(MentorSession).filter(
                MentorSession.program_id == session.program_id,
                MentorSession.session_type == "recorded"
            ).all()

            completed_session_ids = [
                c.session_id for c in db.query(SessionCompletion).filter(
                    SessionCompletion.user_id == current_user.user_id,
                    SessionCompletion.program_id == session.program_id,
                    SessionCompletion.completed == True
                ).all()
            ]

            all_done = all(s.session_id in completed_session_ids for s in all_recorded_sessions)

            if all_done:
                enrollment.status = "certificate_eligible"
                db.commit()

    return {
        "total_watched": merged_unique_seconds,
        "duration_seconds": duration_seconds,
        "percent": round((merged_unique_seconds / duration_seconds * 100) if duration_seconds else 0, 1),
        "is_complete": is_complete
    }


@app.get("/api/video/progress/{session_id}")
def get_video_progress(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns current watch progress for a session — used on page load to restore state."""
    if not current_user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    progress = db.query(VideoProgress).filter(
        VideoProgress.user_id == current_user.user_id,
        VideoProgress.session_id == session_id
    ).first()

    completion = db.query(SessionCompletion).filter(
        SessionCompletion.user_id == current_user.user_id,
        SessionCompletion.session_id == session_id
    ).first()

    session = db.query(MentorSession).filter(
        MentorSession.session_id == session_id
    ).first()

    duration_seconds = (session.duration_minutes or 0) * 60 if session else 0
    total_watched = progress.total_watched if progress else 0

    return {
        "total_watched": total_watched,
        "duration_seconds": duration_seconds,
        "percent": round((total_watched / duration_seconds * 100) if duration_seconds else 0, 1),
        "is_complete": completion.completed if completion else False
    }

@app.post("/session/join/{session_id}")
def join_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logs join time and redirects mentee to the meeting link."""
    if not current_user or current_user.role != "mentee":
        return RedirectResponse(url="/login/mentee", status_code=302)
 
    session = db.query(MentorSession).filter(
        MentorSession.session_id == session_id
    ).first()
    if not session or not session.meeting_link:
        return RedirectResponse(url="/my-sessions", status_code=302)
 
    # Verify enrollment
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.user_id,
        Enrollment.program_id == session.program_id
    ).first()
    if not enrollment:
        return RedirectResponse(url="/my-sessions", status_code=302)
 
    # Get or create attendance record
    attendance = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.user_id == current_user.user_id
    ).first()
 
    if not attendance:
        attendance_id = generate_attendance_id(db)
        attendance = Attendance(
            attendance_id=attendance_id,
            session_id=session_id,
            user_id=current_user.user_id,
            status="absent",
            join_intervals="[]",
            total_minutes_present=0,
            is_auto_marked="false"
        )
        db.add(attendance)
        db.flush()
 
    # Load existing intervals and add new join entry (leave = None for now)
    intervals = json.loads(attendance.join_intervals or "[]")
    intervals.append({
        "join": datetime.now(timezone.utc).isoformat(),
        "leave": None
    })
    attendance.join_intervals = json.dumps(intervals)
    db.commit()
 
    # Redirect to actual meeting
    return RedirectResponse(url=f"/session/live/{session_id}", status_code=302)
 
 
@app.get("/session/live/{session_id}", response_class=HTMLResponse)
def live_session_page(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Intermediate page shown while mentee is in session — has Leave button."""
    if not current_user or current_user.role != "mentee":
        return RedirectResponse(url="/login/mentee", status_code=302)
 
    session = db.query(MentorSession).filter(
        MentorSession.session_id == session_id
    ).first()
    if not session:
        return RedirectResponse(url="/my-sessions", status_code=302)
 
    attendance = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.user_id == current_user.user_id
    ).first()
 
    return templates.TemplateResponse(
        request=request,
        name="live_session.html",
        context={
            "user": current_user,
            "session": session,
            "attendance": attendance
        }
    )
 
 
@app.post("/session/leave/{session_id}")
def leave_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logs leave time, calculates total minutes present, auto marks attendance."""
    if not current_user or current_user.role != "mentee":
        return RedirectResponse(url="/login/mentee", status_code=302)
 
    session = db.query(MentorSession).filter(
        MentorSession.session_id == session_id
    ).first()
    if not session:
        return RedirectResponse(url="/my-sessions", status_code=302)
 
    attendance = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.user_id == current_user.user_id
    ).first()
    if not attendance:
        return RedirectResponse(url="/my-sessions", status_code=302)
 
    # Update the last open interval with leave time
    intervals = json.loads(attendance.join_intervals or "[]")
    leave_time = datetime.now(timezone.utc)
 
    for interval in reversed(intervals):
        if interval["leave"] is None:
            interval["leave"] = leave_time.isoformat()
            break
 
    # Calculate total unique minutes present across all intervals
    total_seconds = 0
    for interval in intervals:
        if interval["join"] and interval["leave"]:
            try:
                join_dt  = datetime.fromisoformat(interval["join"])
                leave_dt = datetime.fromisoformat(interval["leave"])
                diff = (leave_dt - join_dt).total_seconds()
                if diff > 0:
                    total_seconds += diff
            except Exception:
                pass
 
    total_minutes = int(total_seconds / 60)
    duration_minutes = session.duration_minutes or 0
 
    # Auto mark present if >= 90% of session duration attended
    if duration_minutes > 0 and total_minutes >= duration_minutes * 0.90:
        attendance.status = "present"
        attendance.is_auto_marked = "true"
    # Don't override to absent if admin already manually marked present
    elif attendance.is_auto_marked == "false" and attendance.status != "present":
        attendance.status = "absent"
 
    attendance.join_intervals = json.dumps(intervals)
    attendance.total_minutes_present = total_minutes
    db.commit()
 
    return RedirectResponse(url="/my-sessions", status_code=302)
@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="forgot_password.html", context={}
    )
 
 
@app.post("/forgot-password", response_class=HTMLResponse)
def forgot_password_submit(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
 
    # Always show success (don't reveal if email exists — security best practice)
    success_msg = "If that email is registered, you'll receive a reset link shortly."
 
    if user:
        # Invalidate old tokens for this user
        db.query(PasswordResetToken).filter(
    PasswordResetToken.user_id == user.user_id,
    PasswordResetToken.is_used == False).update({"is_used": True}, synchronize_session=False)
 
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(minutes=30)
 
        reset_token = PasswordResetToken(
            token=token,
            user_id=user.user_id,
            is_used=False,
            expires_at=expires
        )
        db.add(reset_token)
        db.commit()
 
        reset_link = f"{BASE_URL}/reset-password?token={token}"
        html = forgot_password_email(user.full_name, reset_link)
 
        # Send in background so page doesn't hang
        threading.Thread(
            target=send_email,
            args=(user.email, "Reset your AgileMentor password", html)
        ).start()
 
    return templates.TemplateResponse(
        request=request,
        name="forgot_password.html",
        context={"success": success_msg}
    )
 
 
@app.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request, token: str, db: Session = Depends(get_db)):
    reset = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.is_used == False
    ).first()
 
    expired = False
    if not reset:
        expired = True
    elif reset.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        expired = True
 
    return templates.TemplateResponse(
        request=request,
        name="reset_password.html",
        context={"token": token, "expired": expired}
    )
 
 
@app.post("/reset-password", response_class=HTMLResponse)
def reset_password_submit(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    reset = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.is_used == False
    ).first()
 
    if not reset or reset.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return templates.TemplateResponse(
            request=request,
            name="reset_password.html",
            context={"token": token, "expired": True}
        )
 
    if password != confirm_password:
        return templates.TemplateResponse(
            request=request,
            name="reset_password.html",
            context={"token": token, "expired": False, "error": "Passwords do not match."}
        )
 
    if not validate_password(password):
        return templates.TemplateResponse(
            request=request,
            name="reset_password.html",
            context={"token": token, "expired": False, "error": "Password must be at least 6 characters and start with a capital letter."}
        )
 
    user = db.query(User).filter(User.user_id == reset.user_id).first()
    user.password_hash = hash_password(password)
    reset.is_used = True
    db.commit()
 
    return RedirectResponse(url=f"/login/{user.role}?reset=success", status_code=302)
 
 
# ── SESSION REMINDER SCHEDULER ────────────────────────────────────────────────
 
def schedule_session_reminder(session_id: str, session_title: str, program_title: str,
                                scheduled_at_dt: datetime, meeting_link: str,
                                mentee_list: list, minutes_before: int = 30):
    """
    Runs in a background thread. Sleeps until 30 min before session, then sends reminder emails.
    mentee_list: list of (full_name, email) tuples
    """
    def run():
        reminder_time = scheduled_at_dt - timedelta(minutes=minutes_before)
        now = datetime.now(timezone.utc)
        sleep_seconds = (reminder_time - now).total_seconds()
 
        if sleep_seconds <= 0:
            return  # Already past reminder time
 
        time.sleep(sleep_seconds)
 
        scheduled_str = scheduled_at_dt.strftime("%d %b %Y, %I:%M %p")
        for full_name, email in mentee_list:
            html = session_reminder_email(
                full_name=full_name,
                session_title=session_title,
                program_title=program_title,
                scheduled_at=scheduled_str,
                meeting_link=meeting_link,
                minutes_before=minutes_before
            )
            send_email(email, f"⏰ Reminder: '{session_title}' starts in {minutes_before} mins", html)
 
    threading.Thread(target=run, daemon=True).start()
 
 
# ── REPLACE admin_create_session WITH THIS ────────────────────────────────────
 
# ── RESOURCES ─────────────────────────────────────────────────────────────────

def detect_file_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "file"
    mapping = {
        "pdf": "pdf",
        "ppt": "ppt", "pptx": "ppt",
        "doc": "doc", "docx": "doc",
        "xls": "excel", "xlsx": "excel",
        "jpg": "image", "jpeg": "image", "png": "image", "gif": "image", "webp": "image",
        "mp4": "video", "mov": "video", "avi": "video", "mkv": "video",
        "txt": "txt",
    }
    return mapping.get(ext, "file")


# ── ADMIN: view resources ─────────────────────────────────────────────────────
@app.get("/admin/resources", response_class=HTMLResponse)
def admin_resources_page(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        return RedirectResponse("/", status_code=302)
    resources = db.query(Resource).order_by(Resource.uploaded_at.desc()).all()
    programs  = db.query(Program).filter(Program.status != "archived").all()
    sessions  = db.query(MentorSession).all()
    return templates.TemplateResponse("admin_resources.html", {
        "request": request, "user": current_user,
        "resources": resources, "programs": programs, "sessions": sessions
    })


# ── ADMIN: upload resource ────────────────────────────────────────────────────
@app.post("/admin/resources/upload")
async def admin_upload_resource(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    program_id: str = Form(""),
    session_id: str = Form(""),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        return RedirectResponse("/", status_code=302)

    contents  = await file.read()
    file_type = detect_file_type(file.filename)
    # images → image resource_type, everything else → raw
    cld_type  = "image" if file_type == "image" else "raw"
    url = upload_file(contents, folder="agilementor/resources", resource_type=cld_type)

    resource = Resource(
        resource_id = generate_resource_id(db),
        title       = title,
        description = description or None,
        file_url    = url,
        file_type   = file_type,
        scope       = "program" if program_id else "global",
        program_id  = program_id or None,
        session_id  = session_id or None,
        uploaded_by = current_user.user_id,
    )
    db.add(resource)
    db.commit()
    return RedirectResponse("/admin/resources", status_code=302)


# ── ADMIN: delete resource ────────────────────────────────────────────────────
@app.post("/admin/resources/delete/{resource_id}")
def admin_delete_resource(
    resource_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        return RedirectResponse("/", status_code=302)
    r = db.query(Resource).filter(Resource.resource_id == resource_id).first()
    if r:
        db.delete(r)
        db.commit()
    return RedirectResponse("/admin/resources", status_code=302)


# ── MENTOR: view resources ────────────────────────────────────────────────────
@app.get("/mentor/resources", response_class=HTMLResponse)
def mentor_resources_page(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "mentor":
        return RedirectResponse("/", status_code=302)

    mentor = db.query(Mentor).filter(Mentor.user_id == current_user.user_id).first()

    # mentor's own uploads + global resources from admin
    own_resources = db.query(Resource).filter(Resource.uploaded_by == current_user.user_id).all()
    global_resources = db.query(Resource).filter(
        Resource.scope == "global",
        Resource.uploaded_by != current_user.user_id
    ).all()

    # programs this mentor is assigned to
    programs = db.query(Program).filter(
        Program.assigned_mentor == mentor.mentor_profile_id
    ).all() if mentor else []

    # sessions for those programs
    prog_ids = [p.program_id for p in programs]
    sessions = db.query(MentorSession).filter(MentorSession.program_id.in_(prog_ids)).all() if prog_ids else []

    # also include program-scoped resources for this mentor's programs
    program_resources = db.query(Resource).filter(
        Resource.scope == "program",
        Resource.program_id.in_(prog_ids),
        Resource.uploaded_by != current_user.user_id
    ).all() if prog_ids else []

    resources = own_resources + global_resources + program_resources

    return templates.TemplateResponse("mentor_resources.html", {
        "request": request, "user": current_user,
        "resources": resources, "programs": programs, "sessions": sessions
    })


# ── MENTOR: upload resource ───────────────────────────────────────────────────
@app.post("/mentor/resources/upload")
async def mentor_upload_resource(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    program_id: str = Form(""),
    session_id: str = Form(""),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "mentor":
        return RedirectResponse("/", status_code=302)

    # mentors can only upload to their assigned programs
    if program_id:
        mentor = db.query(Mentor).filter(Mentor.user_id == current_user.user_id).first()
        prog = db.query(Program).filter(
            Program.program_id == program_id,
            Program.assigned_mentor == mentor.mentor_profile_id
        ).first() if mentor else None
        if not prog:
            raise HTTPException(status_code=403, detail="Not your program")

    contents  = await file.read()
    file_type = detect_file_type(file.filename)
    cld_type  = "image" if file_type == "image" else "raw"
    url = upload_file(contents, folder="agilementor/resources", resource_type=cld_type)

    resource = Resource(
        resource_id = generate_resource_id(db),
        title       = title,
        description = description or None,
        file_url    = url,
        file_type   = file_type,
        scope       = "program",        # mentor uploads are always program-scoped
        program_id  = program_id or None,
        session_id  = session_id or None,
        uploaded_by = current_user.user_id,
    )
    db.add(resource)
    db.commit()
    return RedirectResponse("/mentor/resources", status_code=302)


# ── MENTOR: delete their own resource ────────────────────────────────────────
@app.post("/mentor/resources/delete/{resource_id}")
def mentor_delete_resource(
    resource_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "mentor":
        return RedirectResponse("/", status_code=302)
    r = db.query(Resource).filter(
        Resource.resource_id == resource_id,
        Resource.uploaded_by == current_user.user_id
    ).first()
    if r:
        db.delete(r)
        db.commit()
    return RedirectResponse("/mentor/resources", status_code=302)


# ── MENTEE: view resources ────────────────────────────────────────────────────
@app.get("/my-resources", response_class=HTMLResponse)
def mentee_resources_page(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "mentee":
        return RedirectResponse("/", status_code=302)

    # enrolled program IDs
    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.user_id,
        Enrollment.status == "active"
    ).all()
    prog_ids = [e.program_id for e in enrollments]

    # global resources + resources for enrolled programs
    global_res  = db.query(Resource).filter(Resource.scope == "global").all()
    program_res = db.query(Resource).filter(
        Resource.scope == "program",
        Resource.program_id.in_(prog_ids)
    ).all() if prog_ids else []

    resources = global_res + program_res
    programs  = db.query(Program).filter(Program.program_id.in_(prog_ids)).all() if prog_ids else []

    return templates.TemplateResponse("mentee_resources.html", {
        "request": request, "user": current_user,
        "resources": resources, "programs": programs
    })
    
# ── MENTOR: approve / reject program ─────────────────────────────────────────
@app.post("/mentor/programs/approve/{program_id}")
def mentor_approve_program(
    program_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "mentor":
        return RedirectResponse("/", status_code=302)
    mentor = db.query(Mentor).filter(Mentor.user_id == current_user.user_id).first()
    program = db.query(Program).filter(
        Program.program_id == program_id,
        Program.assigned_mentor == mentor.mentor_profile_id,
        Program.status == "pending"
    ).first() if mentor else None
    if program:
        program.status = "active"
        db.commit()
    return RedirectResponse("/mentor-dashboard", status_code=302)
 
 
@app.post("/mentor/programs/reject/{program_id}")
def mentor_reject_program(
    program_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "mentor":
        return RedirectResponse("/", status_code=302)
    mentor = db.query(Mentor).filter(Mentor.user_id == current_user.user_id).first()
    program = db.query(Program).filter(
        Program.program_id == program_id,
        Program.assigned_mentor == mentor.mentor_profile_id,
        Program.status == "pending"
    ).first() if mentor else None
    if program:
        program.status = "rejected"
        db.commit()
    return RedirectResponse("/mentor-dashboard", status_code=302)

# ── EMAIL VERIFICATION ────────────────────────────────────────────────────────

@app.get("/verify-email", response_class=HTMLResponse)
def verify_email_page(request: Request, user_id: str, email: str):
    return templates.TemplateResponse("verify_email.html", {
        "request": request, "user_id": user_id, "email": email
    })


@app.post("/verify-email", response_class=HTMLResponse)
def verify_email_submit(
    request: Request,
    user_id: str = Form(...),
    otp_code: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return templates.TemplateResponse("verify_email.html", {
            "request": request, "user_id": user_id, "email": "",
            "error": "User not found."
        })

    otp = db.query(EmailOTP).filter(
        EmailOTP.user_id == user_id,
        EmailOTP.otp_code == otp_code,
        EmailOTP.is_used == False
    ).order_by(EmailOTP.created_at.desc()).first()

    if not otp:
        return templates.TemplateResponse("verify_email.html", {
            "request": request, "user_id": user_id, "email": user.email,
            "error": "Invalid OTP. Please try again or request a new one."
        })

    if datetime.now(timezone.utc) > otp.expires_at.replace(tzinfo=timezone.utc):
        return templates.TemplateResponse("verify_email.html", {
            "request": request, "user_id": user_id, "email": user.email,
            "error": "OTP has expired. Please request a new one."
        })

    # mark OTP used and activate user
    otp.is_used = True
    user.status = "active"
    db.commit()

    return RedirectResponse(url=f"/login/{user.role}?verified=1", status_code=302)


@app.post("/resend-otp", response_class=HTMLResponse)
def resend_otp(
    request: Request,
    user_id: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return templates.TemplateResponse("verify_email.html", {
            "request": request, "user_id": user_id, "email": "",
            "error": "User not found."
        })

    # invalidate old OTPs
    db.query(EmailOTP).filter(
        EmailOTP.user_id == user_id,
        EmailOTP.is_used == False
    ).update({"is_used": True})

    otp_code = str(random.randint(100000, 999999))
    otp = EmailOTP(
        otp_id=generate_otp_id(db),
        user_id=user_id,
        otp_code=otp_code,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
    )
    db.add(otp)
    db.commit()

    html = otp_verification_email(full_name=user.full_name, otp_code=otp_code)
    send_email(user.email, "🔐 Your new AgileMentor OTP", html)

    return templates.TemplateResponse("verify_email.html", {
        "request": request, "user_id": user_id, "email": user.email,
        "success": "A new OTP has been sent to your email."
    })