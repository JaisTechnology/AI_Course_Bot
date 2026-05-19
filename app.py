import json
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

import streamlit as st

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    from supabase import Client, create_client
except ImportError:
    Client = None
    create_client = None

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


DATA_FILE = Path(__file__).parent / "course_data.json"
ENV_FILE = Path(__file__).parent / ".env"
DB_FILE = Path(__file__).parent / "automation_assistant.db"
DEFAULT_CHAT_MODEL = "llama-3.3-70b-versatile"
LEADS_TABLE_NAME = "leads"
AUTOMATION_TABLE_NAME = "automation_logs"


def load_courses() -> Dict[str, Dict]:
    with DATA_FILE.open("r", encoding="utf-8") as file:
        raw = json.load(file)
    return {course["name"].lower(): course for course in raw["courses"]}


def get_db_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def get_supabase_url() -> str:
    secret_value = st.secrets.get("SUPABASE_URL", "")
    if secret_value:
        return str(secret_value)
    return os.getenv("SUPABASE_URL", "")


def get_supabase_key() -> str:
    secret_value = st.secrets.get("SUPABASE_KEY", "")
    if secret_value:
        return str(secret_value)
    return os.getenv("SUPABASE_KEY", "")


def use_supabase_storage() -> bool:
    return bool(get_supabase_url() and get_supabase_key())


def get_storage_label() -> str:
    if use_supabase_storage():
        return "Supabase"
    return "SQLite"


def get_supabase_client() -> Client:
    if create_client is None:
        raise RuntimeError("The supabase package is not installed. Run `pip install -r requirements.txt`.")

    supabase_url = get_supabase_url()
    supabase_key = get_supabase_key()
    if not supabase_url or not supabase_key:
        raise RuntimeError("Supabase storage is not configured.")
    return create_client(supabase_url, supabase_key)


def init_db() -> None:
    if use_supabase_storage():
        return

    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                interested_course TEXT NOT NULL,
                message TEXT,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS automation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def log_automation_event(event_type: str, details: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if use_supabase_storage():
        client = get_supabase_client()
        client.table(AUTOMATION_TABLE_NAME).insert(
            {
                "event_type": event_type,
                "details": details,
                "created_at": timestamp,
            }
        ).execute()
        return

    with get_db_connection() as connection:
        connection.execute(
            "INSERT INTO automation_logs (event_type, details, created_at) VALUES (?, ?, ?)",
            (event_type, details, timestamp),
        )
        connection.commit()


def save_lead(full_name: str, email: str, phone: str, interested_course: str, message: str, source: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if use_supabase_storage():
        client = get_supabase_client()
        client.table(LEADS_TABLE_NAME).insert(
            {
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "interested_course": interested_course,
                "message": message,
                "source": source,
                "created_at": timestamp,
            }
        ).execute()
        log_automation_event(
            "lead_capture",
            f"Lead captured for {interested_course} from {full_name} ({email}) via {source}.",
        )
        return

    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO leads (full_name, email, phone, interested_course, message, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (full_name, email, phone, interested_course, message, source, timestamp),
        )
        connection.commit()
    log_automation_event(
        "lead_capture",
        f"Lead captured for {interested_course} from {full_name} ({email}) via {source}.",
    )


def fetch_leads() -> List[Dict[str, str]]:
    if use_supabase_storage():
        client = get_supabase_client()
        response = client.table(LEADS_TABLE_NAME).select("*").order("id", desc=True).execute()
        return [{key: str(value) for key, value in row.items()} for row in response.data]

    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, full_name, email, phone, interested_course, message, source, created_at
            FROM leads
            ORDER BY id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def fetch_automation_logs(limit: int = 10) -> List[Dict[str, str]]:
    if use_supabase_storage():
        client = get_supabase_client()
        response = client.table(AUTOMATION_TABLE_NAME).select("*").order("id", desc=True).limit(limit).execute()
        return [{key: str(value) for key, value in row.items()} for row in response.data]

    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, event_type, details, created_at
            FROM automation_logs
            ORDER BY id DESC
            LIMIT ?
            """
            ,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def load_environment() -> None:
    if load_dotenv is not None and ENV_FILE.exists():
        load_dotenv(ENV_FILE)


def get_api_key() -> str:
    secret_value = st.secrets.get("GROQ_API_KEY", "")
    if secret_value:
        return str(secret_value)
    return os.getenv("GROQ_API_KEY", "")


def get_admin_password() -> str:
    secret_value = st.secrets.get("ADMIN_PASSWORD", "")
    if secret_value:
        return str(secret_value)
    return os.getenv("ADMIN_PASSWORD", "")


def inject_styles() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(249, 115, 22, 0.10), transparent 28%),
                    radial-gradient(circle at top right, rgba(59, 130, 246, 0.10), transparent 24%),
                    #0b1020;
                color: #e5e7eb;
            }

            .block-container {
                max-width: 1120px;
                padding-top: 2.2rem;
                padding-bottom: 2rem;
            }

            [data-testid="stSidebar"] {
                background: rgba(15, 23, 42, 0.94);
                border-right: 1px solid rgba(148, 163, 184, 0.12);
            }

            [data-testid="stSidebar"] .block-container {
                padding-top: 1.6rem;
            }

            .hero-panel {
                position: relative;
                overflow: hidden;
                padding: 1.5rem 1.6rem;
                border: 1px solid rgba(148, 163, 184, 0.18);
                border-radius: 8px;
                background: linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(17, 24, 39, 0.82));
                box-shadow: 0 18px 45px rgba(15, 23, 42, 0.28);
                animation: fade-up 0.55s ease-out;
            }

            .hero-panel::before {
                content: "";
                position: absolute;
                inset: 0;
                background: linear-gradient(120deg, transparent 0%, rgba(255, 255, 255, 0.08) 45%, transparent 100%);
                transform: translateX(-120%);
                animation: sheen 5.2s linear infinite;
            }

            .hero-eyebrow {
                display: inline-flex;
                align-items: center;
                gap: 0.45rem;
                padding: 0.35rem 0.7rem;
                border-radius: 999px;
                background: rgba(249, 115, 22, 0.16);
                color: #fdba74;
                font-size: 0.78rem;
                font-weight: 600;
                letter-spacing: 0;
                margin-bottom: 0.95rem;
            }

            .hero-title {
                font-size: 2.2rem;
                line-height: 1.05;
                font-weight: 700;
                color: #f8fafc;
                margin: 0;
            }

            .hero-subtitle {
                margin: 0.85rem 0 0;
                max-width: 48rem;
                color: #cbd5e1;
                font-size: 1rem;
                line-height: 1.65;
            }

            .stat-card {
                padding: 1rem 1.05rem;
                border: 1px solid rgba(148, 163, 184, 0.16);
                border-radius: 8px;
                background: rgba(15, 23, 42, 0.72);
                min-height: 116px;
                box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
                animation: fade-up 0.7s ease-out;
            }

            .stat-label {
                color: #94a3b8;
                font-size: 0.82rem;
                margin-bottom: 0.5rem;
            }

            .stat-value {
                color: #f8fafc;
                font-size: 1.7rem;
                font-weight: 700;
                line-height: 1;
                margin-bottom: 0.45rem;
            }

            .stat-note {
                color: #cbd5e1;
                font-size: 0.9rem;
                line-height: 1.45;
            }

            .section-label {
                color: #f8fafc;
                font-size: 1rem;
                font-weight: 600;
                margin: 1.2rem 0 0.7rem;
            }

            .suggestion-strip {
                margin: 0.2rem 0 0.4rem;
                color: #94a3b8;
                font-size: 0.92rem;
            }

            .course-card {
                padding: 0.95rem 1rem;
                border: 1px solid rgba(148, 163, 184, 0.12);
                border-radius: 8px;
                background: rgba(15, 23, 42, 0.6);
                margin-bottom: 0.75rem;
                transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
            }

            .course-card:hover {
                transform: translateY(-2px);
                border-color: rgba(249, 115, 22, 0.35);
                background: rgba(30, 41, 59, 0.82);
            }

            .course-name {
                color: #f8fafc;
                font-size: 0.96rem;
                font-weight: 600;
                margin-bottom: 0.35rem;
            }

            .course-meta {
                color: #cbd5e1;
                font-size: 0.84rem;
                line-height: 1.5;
            }

            .panel-card {
                padding: 1rem 1.05rem;
                border: 1px solid rgba(148, 163, 184, 0.14);
                border-radius: 8px;
                background: rgba(15, 23, 42, 0.7);
                margin-bottom: 1rem;
                animation: fade-up 0.45s ease-out;
            }

            .panel-title {
                color: #f8fafc;
                font-size: 1rem;
                font-weight: 600;
                margin-bottom: 0.45rem;
            }

            .panel-copy {
                color: #cbd5e1;
                font-size: 0.92rem;
                line-height: 1.55;
            }

            .admin-shell {
                padding: 1.25rem;
                border: 1px solid rgba(96, 165, 250, 0.18);
                border-radius: 8px;
                background: linear-gradient(145deg, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.82));
                margin-bottom: 1rem;
                animation: fade-up 0.45s ease-out;
            }

            .admin-title {
                color: #f8fafc;
                font-size: 1.15rem;
                font-weight: 700;
                margin-bottom: 0.35rem;
            }

            .admin-copy {
                color: #cbd5e1;
                font-size: 0.92rem;
                line-height: 1.55;
            }

            .admin-lock {
                padding: 1rem 1.05rem;
                border: 1px dashed rgba(248, 113, 113, 0.32);
                border-radius: 8px;
                background: rgba(127, 29, 29, 0.12);
                margin-bottom: 1rem;
            }

            .nav-card {
                padding: 0.9rem 1rem;
                border: 1px solid rgba(148, 163, 184, 0.12);
                border-radius: 8px;
                background: rgba(15, 23, 42, 0.74);
                margin-bottom: 0.9rem;
            }

            [data-testid="stChatMessage"] {
                border: 1px solid rgba(148, 163, 184, 0.12);
                border-radius: 8px;
                background: rgba(15, 23, 42, 0.64);
                animation: fade-up 0.35s ease-out;
            }

            [data-testid="stChatMessageContent"] p {
                line-height: 1.7;
                color: #e5e7eb;
            }

            .stButton > button {
                width: 100%;
                border-radius: 8px;
                border: 1px solid rgba(148, 163, 184, 0.18);
                background: rgba(15, 23, 42, 0.78);
                color: #e5e7eb;
                min-height: 2.8rem;
                transition: all 160ms ease;
            }

            .stButton > button:hover {
                border-color: rgba(249, 115, 22, 0.45);
                color: #fff7ed;
                background: rgba(30, 41, 59, 0.95);
            }

            [data-testid="stChatInput"] {
                border-top: 1px solid rgba(148, 163, 184, 0.1);
                background: rgba(11, 16, 32, 0.92);
            }

            @keyframes fade-up {
                from {
                    opacity: 0;
                    transform: translateY(10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            @keyframes sheen {
                from {
                    transform: translateX(-120%);
                }
                to {
                    transform: translateX(120%);
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def normalize_text(value: str) -> str:
    return " ".join(value.lower().strip().split())


def find_course(question: str, courses: Dict[str, Dict]) -> Dict | None:
    text = normalize_text(question)
    for course_name, course in courses.items():
        if course_name in text:
            return course
        aliases = [normalize_text(alias) for alias in course.get("aliases", [])]
        if any(alias in text for alias in aliases):
            return course
    return None


def extract_topics(question: str) -> List[str]:
    text = normalize_text(question)
    topic_map = {
        "fees": ["fee", "fees", "price", "cost", "tuition"],
        "duration": ["duration", "length", "how long", "months", "weeks"],
        "syllabus": ["syllabus", "curriculum", "topics", "modules", "subjects"],
        "eligibility": ["eligibility", "eligible", "requirements", "criteria"],
        "mode": ["mode", "online", "offline", "weekend", "class timing"],
        "certification": ["certificate", "certification"],
    }

    matches: List[str] = []
    for topic, keywords in topic_map.items():
        if any(keyword in text for keyword in keywords):
            matches.append(topic)
    return matches


def build_context(courses: Dict[str, Dict]) -> str:
    lines: List[str] = []
    for course in courses.values():
        syllabus = ", ".join(course["syllabus"])
        lines.append(
            "\n".join(
                [
                    f"Course: {course['name']}",
                    f"Fees: {course['fees']}",
                    f"Duration: {course['duration']}",
                    f"Mode: {course['mode']}",
                    f"Eligibility: {course['eligibility']}",
                    f"Certification: {course['certification']}",
                    f"Syllabus: {syllabus}",
                ]
            )
        )
    return "\n\n".join(lines)


def get_dashboard_stats(courses: Dict[str, Dict]) -> Tuple[int, int, int]:
    total_courses = len(courses)
    beginner_courses = sum(
        1
        for course in courses.values()
        if "beginner" in course["eligibility"].lower() or "no prior" in course["eligibility"].lower()
    )
    online_courses = sum(1 for course in courses.values() if "online" in course["mode"].lower())
    return total_courses, beginner_courses, online_courses


def get_lead_stats() -> Tuple[int, int]:
    leads = fetch_leads()
    automation_logs = fetch_automation_logs()
    return len(leads), len(automation_logs)


def get_source_breakdown() -> Dict[str, int]:
    leads = fetch_leads()
    breakdown: Dict[str, int] = {}
    for row in leads:
        source = row.get("source", "Unknown")
        breakdown[source] = breakdown.get(source, 0) + 1
    return breakdown


def answer_from_catalog(question: str, courses: Dict[str, Dict]) -> Tuple[str, bool]:
    course = find_course(question, courses)
    topics = extract_topics(question)

    if course:
        if not topics:
            syllabus = ", ".join(course["syllabus"])
            answer = (
                f"{course['name']} costs {course['fees']}, runs for {course['duration']}, "
                f"and is offered in {course['mode']} mode. Eligibility: {course['eligibility']}. "
                f"The syllabus covers {syllabus}. Certification: {course['certification']}."
            )
            return answer, True

        answers: List[str] = [f"Here are the details for {course['name']}:"]
        for topic in topics:
            if topic == "fees":
                answers.append(f"- Fees: {course['fees']}")
            elif topic == "duration":
                answers.append(f"- Duration: {course['duration']}")
            elif topic == "syllabus":
                answers.append(f"- Syllabus: {', '.join(course['syllabus'])}")
            elif topic == "eligibility":
                answers.append(f"- Eligibility: {course['eligibility']}")
            elif topic == "mode":
                answers.append(f"- Mode: {course['mode']}")
            elif topic == "certification":
                answers.append(f"- Certification: {course['certification']}")
        return "\n".join(answers), True

    if "list" in question.lower() or "courses" in question.lower():
        course_names = ", ".join(course["name"] for course in courses.values())
        return f"Available courses are: {course_names}.", True

    return (
        "I could not match that to a course in the local catalog. "
        "Try asking about Python for Data Science, Full Stack Web Development, or UI/UX Design."
    ), False


def answer_with_llm(
    question: str,
    api_key: str,
    model_name: str,
    courses: Dict[str, Dict],
    history: List[Dict[str, str]],
) -> str:
    if Groq is None:
        raise RuntimeError("The groq package is not installed. Run `pip install -r requirements.txt`.")

    client = Groq(api_key=api_key)
    catalog_context = build_context(courses)
    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You are a helpful chatbot for a training institute. "
                "Answer any user prompt clearly and naturally. "
                "When the user asks about courses, use the course catalog below as trusted context. "
                "If the course catalog does not contain a requested course detail, say so plainly instead of inventing it.\n\n"
                f"{catalog_context}"
            ),
        }
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.2,
    )
    return response.choices[0].message.content or "I could not generate a response."


def generate_response(
    prompt: str,
    courses: Dict[str, Dict],
    env_api_key: str,
) -> str:
    fallback_answer, matched = answer_from_catalog(prompt, courses)
    response_text = fallback_answer

    if env_api_key:
        try:
            history = [
                {"role": item["role"], "content": item["content"]}
                for item in st.session_state.messages
            ]
            response_text = answer_with_llm(prompt, env_api_key, DEFAULT_CHAT_MODEL, courses, history)
        except Exception as exc:
            response_text = f"{fallback_answer}\n\nModel call skipped: {exc}"
    elif not matched:
        response_text = (
            f"{fallback_answer}\n\nTip: add GROQ_API_KEY to the .env file to get responses for general prompts too."
        )

    return response_text


def render_dashboard(courses: Dict[str, Dict]) -> None:
    total_courses, beginner_courses, online_courses = get_dashboard_stats(courses)

    st.markdown(
        """
        <div class="hero-panel">
            <div class="hero-eyebrow">Smart Course Guide</div>
            <h1 class="hero-title">Find the right course in a few messages.</h1>
            <p class="hero-subtitle">
                Ask about fees, duration, syllabus, career paths, or compare programs side by side.
                The assistant stays grounded in your course catalog and responds like a polished advisor.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-label">Programs Available</div>
                <div class="stat-value">{total_courses}</div>
                <div class="stat-note">A broader catalog across software, AI, design, and business tracks.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-label">Beginner Friendly</div>
                <div class="stat-value">{beginner_courses}</div>
                <div class="stat-note">Easy-entry options for learners starting from scratch or switching careers.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-label">Online Access</div>
                <div class="stat-value">{online_courses}</div>
                <div class="stat-note">Flexible online and hybrid formats for weekday and weekend learners.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_sidebar(courses: Dict[str, Dict], admin_enabled: bool) -> None:
    with st.sidebar:
        st.header("Workspace")
        admin_card = """
            <div class="nav-card">
                <div class="course-name">Public Assistant</div>
                <div class="course-meta">Chatbot, lead form, and course library for students and prospects.</div>
            </div>
        """
        if admin_enabled:
            admin_card += """
            <div class="nav-card">
                <div class="course-name">Admin Panel</div>
                <div class="course-meta">Protected analytics view for lead records and workflow activity.</div>
            </div>
            """
        st.markdown(admin_card, unsafe_allow_html=True)
        st.markdown("**Course Library**")
        for course in courses.values():
            st.markdown(
                f"""
                <div class="course-card">
                    <div class="course-name">{course['name']}</div>
                    <div class="course-meta">{course['duration']} | {course['fees']}<br>{course['mode']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_lead_form(courses: Dict[str, Dict]) -> None:
    st.markdown(
        """
        <div class="hero-panel">
            <div class="hero-eyebrow">Inquiry Desk</div>
            <h1 class="hero-title">Share your details and we will reach out.</h1>
            <p class="hero-subtitle">
                Use this separate inquiry form for counseling requests, callbacks, and admission interest.
                Every submission is saved and tracked inside the admin workflow.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    course_names = [course["name"] for course in courses.values()]
    with st.form("lead_capture_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
        with col2:
            interested_course = st.selectbox("Interested Course", options=course_names)
            source = st.selectbox("Lead Source", options=["Website Chatbot", "Career Counseling", "Direct Inquiry"])
            message = st.text_area("Message", height=110)
        submitted = st.form_submit_button("Submit Lead")

    if submitted:
        if not full_name.strip() or not email.strip() or not phone.strip():
            st.warning("Please fill in name, email, and phone before submitting the lead.")
        else:
            try:
                save_lead(
                    full_name=full_name.strip(),
                    email=email.strip(),
                    phone=phone.strip(),
                    interested_course=interested_course,
                    message=message.strip(),
                    source=source,
                )
                st.success(f"Lead captured successfully. Stored in {get_storage_label()}.")
            except Exception as exc:
                st.error(f"Lead submission failed: {exc}")


def render_admin_dashboard() -> None:
    leads = fetch_leads()
    logs = fetch_automation_logs()
    source_breakdown = get_source_breakdown()
    latest_source = next(iter(source_breakdown.items()), ("No source yet", 0))

    st.markdown(
        """
        <div class="admin-shell">
            <div class="admin-title">Admin Operations Panel</div>
            <div class="admin-copy">Monitor captured leads, recent automation events, and the current health of your funnel from one place.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-label">Total Leads</div>
                <div class="stat-value">{len(leads)}</div>
                <div class="stat-note">Every form submission is stored in {get_storage_label()} for later follow-up.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-label">Automation Events</div>
                <div class="stat-value">{len(logs)}</div>
                <div class="stat-note">Lead capture workflow writes an event log after each successful submission.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-label">Top Lead Source</div>
                <div class="stat-value">{latest_source[0]}</div>
                <div class="stat-note">{latest_source[1]} submissions currently mapped to this source.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-label">Admin Dashboard</div>', unsafe_allow_html=True)
    tabs = st.tabs(["Lead Records", "Automation Logs"])

    with tabs[0]:
        if leads:
            lead_table = [
                {
                    "Name": row.get("full_name", ""),
                    "Email": row.get("email", ""),
                    "Phone": row.get("phone", ""),
                    "Course": row.get("interested_course", ""),
                    "Source": row.get("source", ""),
                    "Submitted At": row.get("created_at", ""),
                }
                for row in leads
            ]
            st.dataframe(lead_table, use_container_width=True)
        else:
            st.info("No leads captured yet.")

    with tabs[1]:
        if logs:
            log_table = [
                {
                    "Event": row.get("event_type", ""),
                    "Details": row.get("details", ""),
                    "Created At": row.get("created_at", ""),
                }
                for row in logs
            ]
            st.dataframe(log_table, use_container_width=True)
        else:
            st.info("No automation events logged yet.")


def render_admin_panel(admin_password: str) -> None:
    if not admin_password:
        st.markdown(
            """
            <div class="admin-lock">
                <div class="panel-title">Admin panel unavailable</div>
                <div class="panel-copy">Set ADMIN_PASSWORD in .env or Streamlit secrets to enable private admin access.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    st.markdown(
        """
        <div class="hero-panel">
            <div class="hero-eyebrow">Protected Workspace</div>
            <h1 class="hero-title">Admin control for leads and automations.</h1>
            <p class="hero-subtitle">
                Use the admin password to review lead records, inspect automation activity, and present the business workflow separately from the public chatbot view.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.admin_authenticated:
        st.markdown(
            """
            <div class="admin-lock">
                <div class="panel-title">Admin access required</div>
                <div class="panel-copy">This panel is hidden from public users and opens only after password verification.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("admin_login_form"):
            admin_input = st.text_input("Admin Password", type="password")
            login_submitted = st.form_submit_button("Unlock Admin Panel")
        if login_submitted:
            if admin_input == admin_password:
                st.session_state.admin_authenticated = True
                st.success("Admin panel unlocked.")
                st.rerun()
            else:
                st.error("Incorrect admin password.")
        return

    top_col1, top_col2 = st.columns([5, 1])
    with top_col2:
        if st.button("Logout", key="admin_logout"):
            st.session_state.admin_authenticated = False
            st.rerun()

    render_admin_dashboard()


def render_suggestions() -> str | None:
    st.markdown('<div class="section-label">Popular Questions</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="suggestion-strip">Jump into a few good starting points.</div>',
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns(3)
    selected_prompt = None

    with col1:
        if st.button("Compare LLM and Cybersecurity", key="suggest_llm_vs_cyber"):
            selected_prompt = "Compare the LLM Engineering course with Cybersecurity Fundamentals."
    with col2:
        if st.button("Best course for beginners", key="suggest_beginner"):
            selected_prompt = "Which courses are best for beginners with no prior experience?"
    with col3:
        if st.button("Show fees and duration", key="suggest_fees_duration"):
            selected_prompt = "List all available courses with fees and duration."

    return selected_prompt


def main() -> None:
    st.set_page_config(page_title="Course Query Chatbot", layout="centered")
    inject_styles()

    load_environment()
    init_db()
    courses = load_courses()
    env_api_key = get_api_key()
    admin_password = get_admin_password()
    admin_enabled = bool(admin_password)

    render_sidebar(courses, admin_enabled)
    workspace_options = ["Assistant", "Submit Inquiry"]
    if admin_enabled:
        workspace_options.append("Admin Panel")
    panel_mode = st.radio(
        "Workspace View",
        options=workspace_options,
        horizontal=True,
        label_visibility="collapsed",
    )

    if panel_mode == "Admin Panel":
        render_admin_panel(admin_password)
        return

    if panel_mode == "Submit Inquiry":
        render_dashboard(courses)
        render_lead_form(courses)
        return

    render_dashboard(courses)

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hi there. Ask me about fees, duration, syllabus, eligibility, or the best course for your goals.",
            }
        ]

    suggested_prompt = render_suggestions()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask a course question or enter any prompt")
    prompt = prompt or suggested_prompt
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response_text = generate_response(prompt, courses, env_api_key)
            st.markdown(response_text)

    st.session_state.messages.append({"role": "assistant", "content": response_text})


if __name__ == "__main__":
    main()
