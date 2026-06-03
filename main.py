from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

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