# AgileMentor Portal — Database Schema
**Database:** PostgreSQL  
**Version:** 1.1  
**Last Updated:** June 2026

---

## Setup Instructions

1. Create a PostgreSQL database named `agilementor` (or any name you prefer)
2. Run the SQL blocks below **in order**
3. After all tables are created, insert the admin seed user (instructions at the bottom)

---

## Tables

### 1. User
```sql
CREATE TABLE "User" (
    user_id         VARCHAR(10)     PRIMARY KEY,         -- e.g. 26001
    full_name       VARCHAR(100)    NOT NULL,
    email           VARCHAR(150)    NOT NULL UNIQUE,
    password_hash   VARCHAR(255)    NOT NULL,
    role            VARCHAR(10)     NOT NULL CHECK (role IN ('admin', 'mentor', 'mentee')),
    phone           VARCHAR(15),
    status          VARCHAR(10)     DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    profile_photo   VARCHAR(255),
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);
```

---

### 2. Mentor
```sql
CREATE TABLE "Mentor" (
    mentor_profile_id   VARCHAR(10)     PRIMARY KEY,     -- e.g. MTR0001
    user_id             VARCHAR(10)     NOT NULL REFERENCES "User"(user_id),
    expertise           VARCHAR(255),
    experience_years    INTEGER,
    bio                 TEXT,
    linkedin_url        VARCHAR(255)
);
```

---

### 3. MentorInvite
```sql
CREATE TABLE "MentorInvite" (
    invite_id       VARCHAR(10)     PRIMARY KEY,         -- e.g. INV0001
    invite_code     VARCHAR(20)     NOT NULL UNIQUE,
    created_by      VARCHAR(10)     REFERENCES "User"(user_id) ON DELETE SET NULL,
    used_by         VARCHAR(10)     REFERENCES "User"(user_id) ON DELETE SET NULL,
    is_used         BOOLEAN         DEFAULT FALSE,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    expires_at      TIMESTAMP
);
```

---

### 4. MentorCertificate
```sql
CREATE TABLE "MentorCertificate" (
    cert_id             VARCHAR(10)     PRIMARY KEY,     -- e.g. CRT0001
    mentor_profile_id   VARCHAR(10)     REFERENCES "Mentor"(mentor_profile_id),
    title               VARCHAR(200),
    file_url            VARCHAR(255),
    file_type           VARCHAR(10),
    uploaded_at         TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);
```

---

### 5. Programs
```sql
CREATE TABLE "Programs" (
    program_id      VARCHAR(10)     PRIMARY KEY,         -- e.g. PRG0001
    title           VARCHAR(200)    NOT NULL,
    description     TEXT,
    category        VARCHAR(100),
    duration_weeks  INTEGER,
    start_date      DATE,
    end_date        DATE,
    created_by      VARCHAR(10)     REFERENCES "User"(user_id),
    assigned_mentor VARCHAR(10)     REFERENCES "Mentor"(mentor_profile_id),
    status          VARCHAR(15)     DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'completed')),
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);
```

---

### 6. Session
```sql
CREATE TABLE "Session" (
    session_id          VARCHAR(10)     PRIMARY KEY,     -- e.g. SES0001
    program_id          VARCHAR(10)     REFERENCES "Programs"(program_id),
    mentor_id           VARCHAR(10)     REFERENCES "Mentor"(mentor_profile_id),
    title               VARCHAR(200)    NOT NULL,
    description         TEXT,
    session_type        VARCHAR(10)     NOT NULL CHECK (session_type IN ('live', 'recorded')),
    scheduled_at        TIMESTAMP,
    meeting_link        VARCHAR(255),
    video_url           VARCHAR(255),
    duration_minutes    INTEGER,
    status              VARCHAR(15)     DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'cancelled')),
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);
```

---

### 7. Enrollment
> `status` can be `active`, `completed`, or `certificate_eligible`

```sql
CREATE TABLE "Enrollment" (
    enrollment_id   VARCHAR(20)     PRIMARY KEY,         -- e.g. 26PRG00010001
    user_id         VARCHAR(10)     NOT NULL REFERENCES "User"(user_id),
    program_id      VARCHAR(10)     NOT NULL REFERENCES "Programs"(program_id),
    enrollment_date TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    status          VARCHAR(25)     DEFAULT 'active',    -- active | completed | certificate_eligible
    UNIQUE(user_id, program_id)
);
```

---

### 8. Attendence
> Includes auto-attendance fields for live session tracking. Note: table name retains original spelling.

```sql
CREATE TABLE "Attendence" (
    attendance_id           VARCHAR(10)     PRIMARY KEY,    -- e.g. ATT0001
    session_id              VARCHAR(10)     REFERENCES "Session"(session_id),
    user_id                 VARCHAR(10)     REFERENCES "User"(user_id),
    status                  VARCHAR(10)     NOT NULL DEFAULT 'absent' CHECK (status IN ('present', 'absent')),
    marked_at               TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    join_intervals          TEXT            DEFAULT '[]',   -- JSON: [{"join": "ISO", "leave": "ISO"}, ...]
    total_minutes_present   INTEGER         DEFAULT 0,
    is_auto_marked          VARCHAR(5)      DEFAULT 'false',-- "true" if system marked, "false" if manual
    UNIQUE(session_id, user_id)
);
```

---

### 9. VideoProgress
> Tracks watched segments for recorded sessions. Used to enforce anti-skip 95% completion rule.

```sql
CREATE TABLE "VideoProgress" (
    progress_id         VARCHAR(10)     PRIMARY KEY,        -- e.g. VP0001
    user_id             VARCHAR(10)     NOT NULL REFERENCES "User"(user_id),
    session_id          VARCHAR(10)     NOT NULL REFERENCES "Session"(session_id),
    watched_segments    TEXT            DEFAULT '[]',        -- JSON: [[start_sec, end_sec], ...]
    total_watched       INTEGER         DEFAULT 0,           -- unique seconds watched
    last_updated        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, session_id)
);
```

---

### 10. SessionCompletion
> Records when a mentee has fully completed a recorded session (≥95% watched).

```sql
CREATE TABLE "SessionCompletion" (
    completion_id   VARCHAR(10)     PRIMARY KEY,            -- e.g. SC0001
    user_id         VARCHAR(10)     NOT NULL REFERENCES "User"(user_id),
    session_id      VARCHAR(10)     NOT NULL REFERENCES "Session"(session_id),
    program_id      VARCHAR(10)     NOT NULL REFERENCES "Programs"(program_id),
    completed       BOOLEAN         DEFAULT FALSE,
    completed_at    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);
```

---

### 11. Feedback
```sql
CREATE TABLE "Feedback" (
    feedback_id     VARCHAR(10)     PRIMARY KEY,            -- e.g. FBK0001
    session_id      VARCHAR(10)     REFERENCES "Session"(session_id),
    user_id         VARCHAR(10)     REFERENCES "User"(user_id),
    mentor_id       VARCHAR(10)     REFERENCES "Mentor"(mentor_profile_id),
    comment         TEXT,
    submitted_at    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);
```

---

### 12. Announcement
```sql
CREATE TABLE "Announcement" (
    announcement_id VARCHAR(10)     PRIMARY KEY,            -- e.g. ANN0001
    admin_id        VARCHAR(10)     REFERENCES "User"(user_id),
    program_id      VARCHAR(10)     REFERENCES "Programs"(program_id),
    title           VARCHAR(200)    NOT NULL,
    body            TEXT,
    published_at    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);
```

---

### 13. Notification
```sql
CREATE TABLE "Notification" (
    noti_id         VARCHAR(10)     PRIMARY KEY,            -- e.g. NTF0001
    user_id         VARCHAR(10)     REFERENCES "User"(user_id),
    title           VARCHAR(200),
    message         TEXT,
    is_read         BOOLEAN         DEFAULT FALSE,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);
```

---

### 14. Certificate
> Issued to mentees who complete all recorded sessions in a program (status = `certificate_eligible`).

```sql
CREATE TABLE "Certificate" (
    certificate_id  VARCHAR(10)     PRIMARY KEY,            -- e.g. CTR0001
    user_id         VARCHAR(10)     REFERENCES "User"(user_id),
    program_id      VARCHAR(10)     REFERENCES "Programs"(program_id),
    certificate_url VARCHAR(255),
    issued_at       TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);
```

---

## Admin Seed User

After creating all tables, insert the admin user. Generate a bcrypt hash of the password first, then run:

```sql
INSERT INTO "User" (user_id, full_name, email, password_hash, role, status)
VALUES ('26001', 'Admin', 'admin@gmail.com', '<BCRYPT_HASH>', 'admin', 'active');
```

To generate a bcrypt hash in Python:
```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
print(pwd_context.hash("YourPasswordHere"))
```

---

## Changelog

| Version | Change |
|---------|--------|
| 1.0 | Initial schema |
| 1.1 | Added `join_intervals`, `total_minutes_present`, `is_auto_marked` to `Attendence`; added `VideoProgress` and `SessionCompletion` tables; updated `Enrollment.status` to support `certificate_eligible`; fixed `MentorInvite` FK constraints to `ON DELETE SET NULL` |