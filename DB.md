-- ============================================================
--  AgileMentor Portal — Complete Database Schema
--  Database: PostgreSQL
--  Version:  1.0
-- ============================================================

-- ── 1. USER ──────────────────────────────────────────────────
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

-- ── 2. MENTOR ────────────────────────────────────────────────
CREATE TABLE "Mentor" (
    mentor_profile_id   VARCHAR(10)     PRIMARY KEY,     -- e.g. MTR0001
    user_id             VARCHAR(10)     NOT NULL REFERENCES "User"(user_id),
    expertise           VARCHAR(255),
    experience_years    INTEGER,
    bio                 TEXT,
    linkedin_url        VARCHAR(255)
);

-- ── 3. MENTOR INVITE ─────────────────────────────────────────
CREATE TABLE "MentorInvite" (
    invite_id       VARCHAR(10)     PRIMARY KEY,         -- e.g. INV0001
    invite_code     VARCHAR(20)     NOT NULL UNIQUE,
    created_by      VARCHAR(10)     REFERENCES "User"(user_id),
    used_by         VARCHAR(10)     REFERENCES "User"(user_id),
    is_used         BOOLEAN         DEFAULT FALSE,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    expires_at      TIMESTAMP
);

-- ── 4. MENTOR CERTIFICATE ────────────────────────────────────
CREATE TABLE "MentorCertificate" (
    cert_id             VARCHAR(10)     PRIMARY KEY,     -- e.g. CRT0001
    mentor_profile_id   VARCHAR(10)     REFERENCES "Mentor"(mentor_profile_id),
    title               VARCHAR(200),
    file_url            VARCHAR(255),
    file_type           VARCHAR(10),
    uploaded_at         TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

-- ── 5. PROGRAMS ──────────────────────────────────────────────
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

-- ── 6. SESSION ───────────────────────────────────────────────
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

-- ── 7. ENROLLMENT ────────────────────────────────────────────
CREATE TABLE "Enrollment" (
    enrollment_id   VARCHAR(20)     PRIMARY KEY,         -- e.g. 260002 0001 (temp, batch format TBD)
    user_id         VARCHAR(10)     NOT NULL REFERENCES "User"(user_id),
    program_id      VARCHAR(10)     NOT NULL REFERENCES "Programs"(program_id),
    enrollment_date TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    status          VARCHAR(15)     DEFAULT 'active',
    UNIQUE(user_id, program_id)
);

-- ── 8. ATTENDENCE ────────────────────────────────────────────
CREATE TABLE "Attendence" (
    attendance_id   VARCHAR(10)     PRIMARY KEY,         -- e.g. ATT0001
    session_id      VARCHAR(10)     REFERENCES "Session"(session_id),
    user_id         VARCHAR(10)     REFERENCES "User"(user_id),
    status          VARCHAR(10)     NOT NULL CHECK (status IN ('present', 'absent')),
    marked_at       TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, user_id)
);

-- ── 9. FEEDBACK ──────────────────────────────────────────────
CREATE TABLE "Feedback" (
    feedback_id     VARCHAR(10)     PRIMARY KEY,         -- e.g. FBK0001
    session_id      VARCHAR(10)     REFERENCES "Session"(session_id),
    user_id         VARCHAR(10)     REFERENCES "User"(user_id),
    mentor_id       VARCHAR(10)     REFERENCES "Mentor"(mentor_profile_id),
    comment         TEXT,
    submitted_at    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

-- ── 10. ANNOUNCEMENT ─────────────────────────────────────────
CREATE TABLE "Announcement" (
    announcement_id VARCHAR(10)     PRIMARY KEY,         -- e.g. ANN0001
    admin_id        VARCHAR(10)     REFERENCES "User"(user_id),
    program_id      VARCHAR(10)     REFERENCES "Programs"(program_id),
    title           VARCHAR(200)    NOT NULL,
    body            TEXT,
    published_at    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

-- ── 11. NOTIFICATION ─────────────────────────────────────────
CREATE TABLE "Notification" (
    noti_id         VARCHAR(10)     PRIMARY KEY,         -- e.g. NTF0001
    user_id         VARCHAR(10)     REFERENCES "User"(user_id),
    title           VARCHAR(200),
    message         TEXT,
    is_read         BOOLEAN         DEFAULT FALSE,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

-- ── 12. CERTIFICATE ──────────────────────────────────────────
CREATE TABLE "Certificate" (
    certificate_id  VARCHAR(10)     PRIMARY KEY,         -- e.g. CTR0001
    user_id         VARCHAR(10)     REFERENCES "User"(user_id),
    program_id      VARCHAR(10)     REFERENCES "Programs"(program_id),
    certificate_url VARCHAR(255),
    issued_at       TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
--  SEED: Admin user (hardcoded)
--  Password must be bcrypt hashed before inserting.
--  Replace <BCRYPT_HASH> with actual hash.
-- ============================================================
-- INSERT INTO "User" (user_id, full_name, email, password_hash, role, status)
-- VALUES ('26001', 'Admin', 'admin@gmail.com', '<BCRYPT_HASH>', 'admin', 'active');

ALTER TABLE "MentorInvite" DROP CONSTRAINT "MentorInvite_used_by_fkey";
ALTER TABLE "MentorInvite" ADD CONSTRAINT "MentorInvite_used_by_fkey" 
    FOREIGN KEY (used_by) REFERENCES "User"(user_id) ON DELETE SET NULL;

ALTER TABLE "MentorInvite" DROP CONSTRAINT "MentorInvite_created_by_fkey";
ALTER TABLE "MentorInvite" ADD CONSTRAINT "MentorInvite_created_by_fkey" 
    FOREIGN KEY (created_by) REFERENCES "User"(user_id) ON DELETE SET NULL;