# CHIETA LMS

A Django-based web application for managing EISA (Engineering Instructional Support Assessment) tools, including question bank management, assessment uploads, moderation workflows, and user role management.

## Features

* **User Management**: Create and manage users with roles (Administrator, Assessor Developer, Moderator, QCTO Validator, ETQA, Learner, etc.) and qualifications.
* **Question Bank**: CRUD operations on questions, case studies, and MCQs linked to qualifications.
* **Assessment Generation**: Compile papers from the database or AI-generated content, review, and forward to moderators.
* **Assessment Upload**: Upload PDF/DOCX assessments and memos, track status, and assign to moderators/ETQA.
* **Moderation Workflow**: Moderators and QCTO validators can review, approve, or request changes on assessments.
* **Dashboard & Reporting**: Dashboards for each role and reports on assessments, tools generated, and compliance.

## Prerequisites

* Python 3.10+
* PostgreSQL (or adjust to your preferred database engine)
* Git

## Installation

1. **Clone the repository**:

   ```bash
   git clone https://your-repo-url.git
   cd chieta_lms
   ```

2. **Create and activate a virtual environment**:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .\.venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**:

   bash
   pip install -r requirements.txt
   

4. **Configure environment variables**:
   Create a `.env` file in the project root (or set environment variables) with at least:

   ini
   DJANGO_SECRET_KEY=your-django-secret-key
   DATABASE_NAME=chieta_db
   DATABASE_USER=postgres
   DATABASE_PASSWORD=your-db-password
   DATABASE_HOST=localhost
   DATABASE_PORT=5432
   GEMINI_API_KEY=your-google-gemini-api-key  # if using AI features
   

5. **Apply migrations**:

   bash:
   python manage.py migrate


6. Create a superuser:

   bash
   python manage.py createsuperuser
   ```

7. **Collect static files** (optional for production):

   bash
   python manage.py collectstatic
   

## Running the Development Server

bash
python manage.py runserver


Visit `http://127.0.0.1:8000/administrator/login/` to log in as an administrator and start configuring users, qualifications, and assessments.

## Database Setup

The default configuration uses PostgreSQL. To use another database, update the `DATABASES` setting in `chieta_LMS/settings.py` accordingly.

## Default URL Patterns

* `/administrator/login/` – Admin login
* `/administrator/dashboard/` – Admin dashboard (assessment upload & management)
* `/administrator/user-management/` – Manage users, roles, and qualifications
* `/upload_assessment/` – Assessor Developer: upload assessments
* `/assessor/dashboard/` – Assessor Developer dashboard
* `/generate-paper/` – Generate assessment from question bank
* `/moderator/` – Moderator Developer dashboard
* `/qcto/dashboard/` – QCTO validator dashboard
* `/` – Redirects to Assessor Developer dashboard by default

## Configuration Highlights

* **Custom User Model**: Defined in `core/models.py` (`CustomUser` extends `AbstractUser`).
* **Qualifications**: Predefined mapping in `Qualification` model; can add more via admin.
* **Assessment Model**: Includes `created_by` (uploader) and status workflow.
* **AI Integration**: Optional Google Gemini via `genai_client` if `GEMINI_API_KEY` is set.

## Testing--no tests yet

bash:
python manage.py test


## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/name`)
3. Commit your changes (`git commit -m "feat: ..."`)
4. Push to the branch (`git push origin feature/name`)
5. Open a pull request

License

© JBS
