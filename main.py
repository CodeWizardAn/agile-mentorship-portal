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
    return templates.TemplateResponse(
        request=request, name="signup.html", context={"role": role}
    )

@app.get("/login/{role}", response_class=HTMLResponse)
def login(request: Request, role: str):
    return templates.TemplateResponse(
        request=request, name="login.html", context={"role": role}
    )

@app.get("/mentor-dashboard", response_class=HTMLResponse)
def mentor_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="mentor_dashboard.html")

@app.get("/mentee-dashboard", response_class=HTMLResponse)
def mentee_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="mentee_dashboard.html")

@app.get("/admin-dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="admin_dashboard.html")


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
    # mentor invite code check
    if role == "mentor":
        if not invite_code:
            return HTMLResponse(
                "<h2>Invite code is required for mentor signup</h2>",
                status_code=400
            )
        invite = db.query(MentorInvite).filter(
            MentorInvite.invite_code == invite_code.upper(),
            MentorInvite.is_used == False
        ).first()
        if not invite:
            return HTMLResponse(
                "<h2>Invalid or already used invite code</h2>",
                status_code=400
            )

    # email validation
    if not validate_email(email):
        return HTMLResponse(
            "<h2>Invalid email. Use a valid domain like gmail.com, yahoo.com, ac.in etc.</h2>",
            status_code=400
        )

    # password validation
    if not validate_password(password):
        return HTMLResponse(
            "<h2>Password must be at least 6 characters and start with a capital letter</h2>",
            status_code=400
        )

    # check if email already registered
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return HTMLResponse("<h2>Email already registered</h2>", status_code=400)

    user_id = generate_user_id(db)

    user = User(
        user_id=user_id,
        full_name=full_name,
        email=email,
        password_hash=hash_password(password),
        role=role.lower(),
        status="active"
    )
    db.add(user)
    db.flush()

    # if mentor — create mentor profile and mark invite used
    if role == "mentor":
        mentor_profile_id = generate_mentor_id(db)
        mentor = Mentor(
            mentor_profile_id=mentor_profile_id,
            user_id=user_id,
        )
        db.add(mentor)
        invite.is_used = True
        invite.used_by = user_id
        db.commit()
        return {
            "message": "Mentor account created successfully",
            "user_id": user_id,
            "mentor_profile_id": mentor_profile_id
        }

    db.commit()
    return {"message": "User created successfully", "user_id": user_id}


# ── LOGIN ─────────────────────────────────────────────────────────────────────

@app.post("/login/{role}")
def login_user(
    role: str,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    if not validate_email(email):
        return HTMLResponse(
            "<h2>Invalid email. Use a valid domain like gmail.com, yahoo.com, ac.in etc.</h2>",
            status_code=400
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return HTMLResponse("<h2>User not found</h2>", status_code=404)

    if user.role != role.lower():
        return HTMLResponse("<h2>Invalid role for this account</h2>", status_code=403)

    if not verify_password(password, user.password_hash):
        return HTMLResponse("<h2>Invalid password</h2>", status_code=401)

    token = create_access_token(data={
        "user_id": user.user_id,
        "role": user.role,
        "email": user.email
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
        return HTMLResponse("<h2>Unauthorized. Admins only.</h2>", status_code=403)

    invite_code = secrets.token_hex(6).upper()
    invite_id = generate_invite_id(db)

    invite = MentorInvite(
        invite_id=invite_id,
        invite_code=invite_code,
        created_by=admin.user_id,
        is_used=False
    )

    db.add(invite)
    db.commit()

    return {"invite_code": invite_code, "invite_id": invite_id}


# ── MENTOR PROFILE ────────────────────────────────────────────────────────────

@app.get("/mentor-profile", response_class=HTMLResponse)
def mentor_profile_page(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user or current_user.role != "mentor":
        return RedirectResponse(url="/login/mentor", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="mentor_profile.html",
        context={"user": current_user}
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
        return HTMLResponse("<h2>Unauthorized</h2>", status_code=403)

    mentor = db.query(Mentor).filter(Mentor.user_id == current_user.user_id).first()
    if not mentor:
        return HTMLResponse("<h2>Mentor profile not found</h2>", status_code=404)

    if expertise:
        mentor.expertise = expertise
    if experience_years:
        mentor.experience_years = experience_years
    if bio:
        mentor.bio = bio
    if linkedin_url:
        mentor.linkedin_url = linkedin_url

    db.commit()

    return {"message": "Profile updated successfully", "mentor_profile_id": mentor.mentor_profile_id}


# ── PROGRAMS ──────────────────────────────────────────────────────────────────

@app.get("/admin/programs", response_class=HTMLResponse)
def programs_page(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user or current_user.role != "admin":
        return RedirectResponse(url="/login/admin", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="programs.html",
        context={"user": current_user}
    )


@app.post("/admin/programs/create")
def create_program(
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
        return HTMLResponse("<h2>Unauthorized</h2>", status_code=403)

    program_id = generate_program_id(db)

    program = Program(
        program_id=program_id,
        title=title,
        description=description,
        category=category,
        duration_weeks=duration_weeks,
        start_date=start_date,
        end_date=end_date,
        created_by=current_user.user_id,
        assigned_mentor=assigned_mentor if assigned_mentor else None,
        status="draft"
    )

    db.add(program)
    db.commit()

    return {"message": "Program created successfully", "program_id": program_id}


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
        return HTMLResponse("<h2>Unauthorized</h2>", status_code=403)

    program = db.query(Program).filter(Program.program_id == program_id).first()
    if not program:
        return HTMLResponse("<h2>Program not found</h2>", status_code=404)

    if title: program.title = title
    if description: program.description = description
    if category: program.category = category
    if duration_weeks: program.duration_weeks = duration_weeks
    if start_date: program.start_date = start_date
    if end_date: program.end_date = end_date
    if assigned_mentor: program.assigned_mentor = assigned_mentor
    if status: program.status = status

    db.commit()

    return {"message": "Program updated successfully", "program_id": program_id}


@app.post("/admin/programs/delete/{program_id}")
def delete_program(
    program_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "admin":
        return HTMLResponse("<h2>Unauthorized</h2>", status_code=403)

    program = db.query(Program).filter(Program.program_id == program_id).first()
    if not program:
        return HTMLResponse("<h2>Program not found</h2>", status_code=404)

    db.delete(program)
    db.commit()

    return {"message": "Program deleted successfully"}


@app.get("/programs", response_class=HTMLResponse)
def view_programs(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user:
        return RedirectResponse(url="/login/mentee", status_code=302)
    programs = db.query(Program).filter(Program.status == "active").all()
    return templates.TemplateResponse(
        request=request,
        name="view_programs.html",
        context={"programs": programs, "user": current_user}
    )