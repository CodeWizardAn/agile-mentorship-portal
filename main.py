from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
import re
import secrets
from security import hash_password, verify_password
from database import get_db
from models.user import User
from models.mentor_invite import MentorInvite
from models.mentor import Mentor

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
    invite_code: str = Form(None),  # optional, only required for mentor
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

    # generate user_id
    year = str(datetime.now().year)[2:]
    count = db.query(User).count() + 1
    user_id = f"{year}{count:03d}"

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
        mentor_count = db.query(Mentor).count() + 1
        mentor_profile_id = f"MTR{mentor_count:04d}"
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
    # email validation
    if not validate_email(email):
        return HTMLResponse(
            "<h2>Invalid email. Use a valid domain like gmail.com, yahoo.com, ac.in etc.</h2>",
            status_code=400
        )

    # check if user exists
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return HTMLResponse("<h2>User not found</h2>", status_code=404)

    # check role matches
    if user.role != role.lower():
        return HTMLResponse("<h2>Invalid role for this account</h2>", status_code=403)

    # verify password
    if not verify_password(password, user.password_hash):
        return HTMLResponse("<h2>Invalid password</h2>", status_code=401)

    # redirect based on role
    if user.role == "mentor":
        return RedirectResponse(url="/mentor-dashboard", status_code=302)
    elif user.role == "mentee":
        return RedirectResponse(url="/mentee-dashboard", status_code=302)
    elif user.role == "admin":
        return RedirectResponse(url="/admin-dashboard", status_code=302)


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

    count = db.query(MentorInvite).count() + 1
    invite_id = f"INV{count:04d}"

    invite = MentorInvite(
        invite_id=invite_id,
        invite_code=invite_code,
        created_by=admin.user_id,
        is_used=False
    )

    db.add(invite)
    db.commit()

    return {"invite_code": invite_code, "invite_id": invite_id}