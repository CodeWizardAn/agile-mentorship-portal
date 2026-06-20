import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

load_dotenv()

GMAIL_USER     = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Send an HTML email via Gmail SMTP. Returns True on success."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"AgileMentor <{GMAIL_USER}>"
        msg["To"]      = to_email

        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())

        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send to {to_email}: {e}")
        return False


# ── EMAIL TEMPLATES ───────────────────────────────────────────────────────────

def forgot_password_email(full_name: str, reset_link: str) -> str:
    return f"""
    <div style="font-family:'Inter',sans-serif;max-width:560px;margin:0 auto;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #E2E8F4;">
      <div style="background:linear-gradient(135deg,#0F2645,#1a3a6b);padding:32px 36px;">
        <div style="font-size:1.2rem;font-weight:800;color:white;letter-spacing:-0.3px;">Agile<span style="color:#60A5FA;">Mentor</span></div>
      </div>
      <div style="padding:36px;">
        <h2 style="font-size:1.3rem;font-weight:700;color:#0F2645;margin-bottom:8px;">Reset your password</h2>
        <p style="font-size:0.9rem;color:#64748B;margin-bottom:24px;line-height:1.6;">
          Hi {full_name}, we received a request to reset your AgileMentor password.
          Click the button below to set a new one. This link expires in <strong>30 minutes</strong>.
        </p>
        <a href="{reset_link}" style="display:inline-block;padding:13px 28px;background:linear-gradient(135deg,#2563EB,#0EA5E9);color:white;font-weight:700;font-size:0.9rem;border-radius:10px;text-decoration:none;">
          Reset Password →
        </a>
        <p style="font-size:0.78rem;color:#94A3B8;margin-top:24px;line-height:1.6;">
          If you didn't request this, you can safely ignore this email. Your password won't change.
        </p>
        <hr style="border:none;border-top:1px solid #E2E8F4;margin:24px 0;"/>
        <p style="font-size:0.75rem;color:#CBD5E1;">© 2026 AgileMentor. All rights reserved.</p>
      </div>
    </div>
    """


def session_created_email(full_name: str, session_title: str, session_type: str,
                           program_title: str, scheduled_at: str, meeting_link: str = None,
                           video_url: str = None) -> str:
    action_block = ""
    if session_type == "live" and meeting_link:
        action_block = f"""
        <a href="{meeting_link}" style="display:inline-block;padding:11px 24px;background:linear-gradient(135deg,#2563EB,#0EA5E9);color:white;font-weight:700;font-size:0.85rem;border-radius:9px;text-decoration:none;">
          Join Session →
        </a>"""
    elif session_type == "recorded" and video_url:
        action_block = f"""
        <a href="{video_url}" style="display:inline-block;padding:11px 24px;border:2px solid #2563EB;color:#2563EB;font-weight:700;font-size:0.85rem;border-radius:9px;text-decoration:none;">
          Watch Video →
        </a>"""

    type_badge_color = "#FEE2E2" if session_type == "live" else "#EEF2FF"
    type_text_color  = "#DC2626" if session_type == "live" else "#4338CA"
    type_emoji       = "🔴" if session_type == "live" else "🎬"

    return f"""
    <div style="font-family:'Inter',sans-serif;max-width:560px;margin:0 auto;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #E2E8F4;">
      <div style="background:linear-gradient(135deg,#0F2645,#1a3a6b);padding:32px 36px;">
        <div style="font-size:1.2rem;font-weight:800;color:white;">Agile<span style="color:#60A5FA;">Mentor</span></div>
      </div>
      <div style="padding:36px;">
        <div style="display:inline-block;padding:4px 12px;background:{type_badge_color};color:{type_text_color};font-size:0.75rem;font-weight:700;border-radius:20px;margin-bottom:16px;">
          {type_emoji} {session_type.upper()} SESSION
        </div>
        <h2 style="font-size:1.2rem;font-weight:700;color:#0F2645;margin-bottom:6px;">New Session Added</h2>
        <p style="font-size:0.88rem;color:#64748B;margin-bottom:20px;">Hi {full_name}, a new session has been added to <strong>{program_title}</strong>.</p>
        <div style="background:#F4F7FF;border-radius:12px;padding:18px 20px;margin-bottom:24px;">
          <div style="font-size:1rem;font-weight:700;color:#0F2645;margin-bottom:8px;">{session_title}</div>
          <div style="font-size:0.82rem;color:#64748B;">📅 {scheduled_at if scheduled_at else 'Available anytime'}</div>
        </div>
        {action_block}
        <hr style="border:none;border-top:1px solid #E2E8F4;margin:24px 0;"/>
        <p style="font-size:0.75rem;color:#CBD5E1;">© 2026 AgileMentor. All rights reserved.</p>
      </div>
    </div>
    """


def session_reminder_email(full_name: str, session_title: str, program_title: str,
                            scheduled_at: str, meeting_link: str, minutes_before: int) -> str:
    return f"""
    <div style="font-family:'Inter',sans-serif;max-width:560px;margin:0 auto;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #E2E8F4;">
      <div style="background:linear-gradient(135deg,#0F2645,#1a3a6b);padding:32px 36px;">
        <div style="font-size:1.2rem;font-weight:800;color:white;">Agile<span style="color:#60A5FA;">Mentor</span></div>
      </div>
      <div style="padding:36px;">
        <div style="display:inline-block;padding:4px 12px;background:#FEF3C7;color:#92400E;font-size:0.75rem;font-weight:700;border-radius:20px;margin-bottom:16px;">
          ⏰ REMINDER
        </div>
        <h2 style="font-size:1.2rem;font-weight:700;color:#0F2645;margin-bottom:6px;">Session starting in {minutes_before} minutes!</h2>
        <p style="font-size:0.88rem;color:#64748B;margin-bottom:20px;">Hi {full_name}, your session in <strong>{program_title}</strong> is about to begin.</p>
        <div style="background:#F4F7FF;border-radius:12px;padding:18px 20px;margin-bottom:24px;">
          <div style="font-size:1rem;font-weight:700;color:#0F2645;margin-bottom:8px;">🔴 {session_title}</div>
          <div style="font-size:0.82rem;color:#64748B;">📅 {scheduled_at}</div>
        </div>
        <a href="{meeting_link}" style="display:inline-block;padding:13px 28px;background:linear-gradient(135deg,#2563EB,#0EA5E9);color:white;font-weight:700;font-size:0.9rem;border-radius:10px;text-decoration:none;">
          Join Now →
        </a>
        <hr style="border:none;border-top:1px solid #E2E8F4;margin:24px 0;"/>
        <p style="font-size:0.75rem;color:#CBD5E1;">© 2026 AgileMentor. All rights reserved.</p>
      </div>
    </div>
    """
def enrollment_confirmation_email(full_name: str, program_title: str, 
                                   program_description: str, start_date: str) -> str:
    return f"""
    <div style="font-family:'Inter',sans-serif;max-width:560px;margin:0 auto;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #E2E8F4;">
      <div style="background:linear-gradient(135deg,#0F2645,#1a3a6b);padding:32px 36px;">
        <div style="font-size:1.2rem;font-weight:800;color:white;">Agile<span style="color:#60A5FA;">Mentor</span></div>
      </div>
      <div style="padding:36px;">
        <div style="display:inline-block;padding:4px 12px;background:#DCFCE7;color:#15803D;font-size:0.75rem;font-weight:700;border-radius:20px;margin-bottom:16px;">
          ✅ ENROLLMENT CONFIRMED
        </div>
        <h2 style="font-size:1.2rem;font-weight:700;color:#0F2645;margin-bottom:6px;">You're enrolled!</h2>
        <p style="font-size:0.88rem;color:#64748B;margin-bottom:20px;">Hi {full_name}, you've successfully enrolled in the following program on AgileMentor.</p>
        <div style="background:#F4F7FF;border-radius:12px;padding:18px 20px;margin-bottom:24px;">
          <div style="font-size:1rem;font-weight:700;color:#0F2645;margin-bottom:6px;">{program_title}</div>
          <div style="font-size:0.82rem;color:#64748B;margin-bottom:4px;">📝 {program_description or 'No description provided.'}</div>
          <div style="font-size:0.82rem;color:#64748B;">📅 Starts: {start_date if start_date else 'Flexible'}</div>
        </div>
        <p style="font-size:0.82rem;color:#64748B;margin-bottom:20px;">Head to your dashboard to view sessions and track your progress.</p>
        <hr style="border:none;border-top:1px solid #E2E8F4;margin:24px 0;"/>
        <p style="font-size:0.75rem;color:#CBD5E1;">© 2026 AgileMentor. All rights reserved.</p>
      </div>
    </div>
    """