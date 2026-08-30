CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK(role IN ('candidate', 'employer'))
);

CREATE TABLE IF NOT EXISTS candidates (
    user_id            INTEGER PRIMARY KEY,
    full_name          TEXT NOT NULL,
    contact            TEXT,
    education          TEXT,
    major              TEXT,
    years_experience   INTEGER DEFAULT 0,
    work_experience    TEXT,
    skills             TEXT,
    preferred_mode     TEXT CHECK(preferred_mode IN ('Remote','On-site','Hybrid')),
    preferred_location TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS jobs (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    employer_id        INTEGER NOT NULL,
    title              TEXT NOT NULL,
    description        TEXT NOT NULL,
    company            TEXT,
    required_education TEXT,
    required_skills    TEXT,
    years_experience   INTEGER DEFAULT 0,
    work_mode          TEXT CHECK(work_mode IN ('Remote','On-site','Hybrid')),
    location           TEXT,
    FOREIGN KEY (employer_id) REFERENCES users(id)
);