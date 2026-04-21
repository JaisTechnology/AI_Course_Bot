import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


DATA_FILE = Path(__file__).parent / "course_data.json"
ENV_FILE = Path(__file__).parent / ".env"
DEFAULT_CHAT_MODEL = "llama-3.3-70b-versatile"


def load_courses() -> Dict[str, Dict]:
    with DATA_FILE.open("r", encoding="utf-8") as file:
        raw = json.load(file)
    return {course["name"].lower(): course for course in raw["courses"]}


def load_environment() -> None:
    if load_dotenv is not None and ENV_FILE.exists():
        load_dotenv(ENV_FILE)


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


def render_sidebar(courses: Dict[str, Dict]) -> None:
    with st.sidebar:
        st.header("Course Library")
        st.caption("Explore the catalog")
        for course in courses.values():
            st.markdown(
                f"""
                <div class="course-card">
                    <div class="course-name">{course['name']}</div>
                    <div class="course-meta">{course['duration']} • {course['fees']}<br>{course['mode']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


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
    courses = load_courses()
    env_api_key = os.getenv("GROQ_API_KEY", "")

    render_sidebar(courses)
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
