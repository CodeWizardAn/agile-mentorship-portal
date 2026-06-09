from aiohttp import request
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Form
from fastapi import Depends
from sqlalchemy.orm import Session
from security import hash_password
from database import get_db
from models import User

app = FastAPI()

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html"
    )
    
@app.get("/signup/{role}", response_class=HTMLResponse)
def signup(request: Request, role: str):
    return templates.TemplateResponse(
        request=request,
        name="signup.html",
        context={
            "role": role
        }
    )


@app.get("/login/{role}", response_class=HTMLResponse)
def login(request: Request, role: str):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "role": role
        }
    )
    
@app.get("/mentor-dashboard", response_class=HTMLResponse)
def mentor_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="mentor_dashboard.html"
    )


@app.get("/mentee-dashboard", response_class=HTMLResponse)
def mentee_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="mentee_dashboard.html"
    )


@app.get("/admin-dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html"
    )
    
@app.post("/signup/{role}")
def create_user(
    role: str,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return HTMLResponse(
            "<h2>Email already registered</h2>",
            status_code=400
    )
    user = User(
        full_name=full_name,
        email=email,
        password_hash=hash_password(password),
        role=role.upper(),
        status="ACTIVE"
    )

    db.add(user)
    db.commit()

    return {
        "message": "User created successfully"
    }