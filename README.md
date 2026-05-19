# AI-Powered Business Automation Assistant

An AI-powered Streamlit application that combines a course-aware chatbot, lead capture system, automation workflow, SQLite storage, and a lightweight admin dashboard using the Groq API.

## Features

- AI chatbot for business and course-related queries
- Lead capture form for collecting student or customer interest
- SQLite database for storing leads and automation logs
- Automation workflow: form submission -> lead storage -> automation event logging
- Admin dashboard for viewing submitted leads and recent automation events
- Groq API support for model-based responses
- Works even without an API key for known course questions

## Run locally

1. Install Python 3.10+.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project folder and add:

   ```env
   GROQ_API_KEY=your_api_key_here
   ```

4. Start the app:

   ```bash
   streamlit run app.py
   ```

5. Open the local URL shown by Streamlit.

## Project modules

1. Chatbot module
   - Handles course questions and general prompts
   - Uses Groq API with local course catalog context

2. Lead capture module
   - Collects name, email, phone, interested course, and message

3. Data storage module
   - Stores leads and automation logs in `automation_assistant.db`

4. Automation workflow
   - On lead form submission, the app stores the lead and logs an automation event

5. Admin dashboard
   - Displays captured leads and recent automation activity

## Files

- `app.py` - main Streamlit application
- `course_data.json` - course catalog and structured knowledge base
- `automation_assistant.db` - SQLite database created automatically at runtime

## Customize courses

Edit `course_data.json` to add or update courses.
