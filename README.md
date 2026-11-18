# Campus Connect - Flask + SQLite Backend

Backend for **Campus Connect - Integrated Student Enrollment and Information System**.
It combines the Laboratory 3 course management API with the Laboratory 4 portal
data (students, enrollments, announcements) behind one REST API.

The frontend is the separate Campus Connect portal hosted on Base44. This folder
is the Python backend and is NOT hosted by Base44.

## 1. Project structure

    Campus-Connect/
      app.py                  Flask app, database setup, REST API, sample data
      database.db             created automatically on first run (do not commit)
      requirements.txt
      README.md
      .gitignore
      run.bat                 one-click setup + run on Windows
      start.bat               run again after run.bat
      templates/
        index.html            dashboard page
        students.html
        courses.html
        enrollment.html
        announcements.html
      static/
        css/style.css
        javascript/script.js
        images/
      screenshots/

## 2. Run it on Windows

1. Install Python 3.10+ from python.org (tick "Add Python to PATH").
2. Put all files in a folder called Campus-Connect.
3. Double-click **run.bat**. It creates a virtual environment, installs the
   requirements and starts the server.
4. Open http://127.0.0.1:5000/api/health in a browser. You should see JSON with
   "status": "ok".
5. The API base URL for the frontend is **http://127.0.0.1:5000/api**.

Manual alternative:

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    python app.py

## 3. Database

database.db is created automatically the first time the app starts, together
with the five tables (students, courses, enrollments, announcements, users) and
a small set of fictional sample records. Foreign keys are enforced
(PRAGMA foreign_keys = ON) and enrollments has a UNIQUE (student_id, course_id)
constraint so the same student cannot be enrolled twice in the same course.

To reset the data: stop the server, delete database.db, start it again.

## 4. REST API

All responses are JSON. Errors look like {"error": "message"} with a 4xx/5xx status.

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | /api/health | Service and database check |
| GET | /api/stats | Dashboard totals, status counts, 7-day trend, recent rows |
| GET | /api/students | List students (?q= search) |
| POST | /api/students | Create a student |
| GET | /api/students/id | One student |
| PUT | /api/students/id | Update a student |
| DELETE | /api/students/id | Delete a student (409 if enrollments exist) |
| GET | /api/courses | List courses (?q= search, includes enrolled count) |
| POST | /api/courses | Create a course |
| GET | /api/courses/id | One course |
| PUT | /api/courses/id | Update a course |
| DELETE | /api/courses/id | Delete a course (409 if enrollments exist) |
| GET | /api/enrollments | List enrollments (?q=, ?status=, ?student_id=) |
| POST | /api/enrollments | Enroll a student (409 on duplicate) |
| GET | /api/enrollments/id | One enrollment |
| PUT | /api/enrollments/id | Change status (Pending/Approved/Rejected/Cancelled) |
| DELETE | /api/enrollments/id | Delete an enrollment |
| GET | /api/announcements | List announcements |
| POST | /api/announcements | Create an announcement |
| GET | /api/announcements/id | One announcement |
| PUT | /api/announcements/id | Update an announcement |
| DELETE | /api/announcements/id | Delete an announcement |

Example body for POST /api/enrollments:

    {"student_id": 1, "course_id": 3}

student_id and course_id are the numeric primary keys from /api/students and
/api/courses. The human-readable student number is returned as student_number.

## 5. Push to GitHub

    git init
    git add .
    git commit -m "Campus Connect Flask backend"
    git branch -M main
    git remote add origin https://github.com/YOUR-USERNAME/campus-connect-backend.git
    git push -u origin main

.gitignore already excludes database.db and .venv. This project needs no secrets.

## 6. Deploy to Render

1. Push the project to GitHub (step 5).
2. On Render: New + > Web Service, connect the repository.
3. Settings:
   - Environment: Python 3
   - Build command: pip install -r requirements.txt
   - Start command: gunicorn app:app
4. Create the service and wait for the deploy to finish.
5. Your API base URL becomes https://YOUR-SERVICE.onrender.com/api
6. Test it: https://YOUR-SERVICE.onrender.com/api/health

### Keeping SQLite data

Render's default filesystem is ephemeral: the SQLite file is recreated and the
sample data is re-seeded after every restart or redeploy. To keep real data, add
a persistent disk (paid Render plan) mounted at e.g. /var/data and set the
environment variable DATABASE_PATH=/var/data/database.db.

## 7. Connect the frontend

1. Open the Campus Connect portal.
2. Go to Settings.
3. Paste the API base URL (http://127.0.0.1:5000/api locally, or
   https://YOUR-SERVICE.onrender.com/api on Render) and press Save.
4. Press Test - you should see "Connected".

### CORS

The backend enables CORS for all origins so the hosted frontend can call it.
For production, restrict it:

    CORS(app, origins=["https://your-app.base44.app"])

## 8. Quick API tests in a browser

Open these addresses directly (GET requests):

- http://127.0.0.1:5000/api/health
- http://127.0.0.1:5000/api/students
- http://127.0.0.1:5000/api/courses
- http://127.0.0.1:5000/api/enrollments
- http://127.0.0.1:5000/api/announcements
- http://127.0.0.1:5000/api/stats

POST / PUT / DELETE need Postman, Insomnia or curl, for example:

    curl -X POST http://127.0.0.1:5000/api/students -H "Content-Type: application/json" -d "{\"student_id\":\"2024-0100\",\"first_name\":\"Test\",\"last_name\":\"Student\",\"email\":\"test@campusconnect.edu\",\"program\":\"BS Computer Science\",\"year_level\":1}"
