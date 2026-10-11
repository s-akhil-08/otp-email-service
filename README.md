# 🔐 OTP & Email Service: Django Microservice

> A standalone Django REST microservice that handles email OTP verification, password recovery, and notification emails. It runs separately from the main API and is designed to be **deployed on Vercel** (serverless), so OTP emails never wait on a sleeping free-tier server.

[![Django](https://img.shields.io/badge/Django-5.x-092E20?style=flat-square&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-REST-red?style=flat-square&logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-336791?style=flat-square&logo=postgresql&logoColor=white)](https://supabase.com/)
[![Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-000000?style=flat-square&logo=vercel&logoColor=white)](https://vercel.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

Part of a three-repo project:

| Repo | Role |
| :--- | :--- |
| [cadverse-frontend](https://github.com/s-akhil-08/cadverse-frontend) | React app that calls this service for signup, OTP, and reset flows |
| [cadverse-platform-backend](https://github.com/s-akhil-08/cadverse-platform-backend) | Main API (projects, files, feedback) and admin |
| **otp-email-service** (this repo) | OTP, password recovery, and email notifications |

---

## 🌐 Why a Separate Service on Vercel?

- **No cold-start delay for OTP:** the main API runs on a free tier that sleeps when idle. Verification emails need to go out immediately, so this service runs as a serverless function on Vercel instead.
- **Independent scaling and failure:** if the main API is down or waking up, signup and password reset still work.
- **Clear separation:** email credentials and authentication logic live in one small codebase.

> [!WARNING]
> **Serverless note:** Vercel functions don't share memory between requests. The default `LocMemCache` used for OTP storage works locally and on a single long-running server (Render), but on Vercel you should store OTPs in a shared place, such as the database or a Redis cache (for example Upstash). See [Deployment on Vercel](#-deployment-on-vercel).

---

## ✨ Features

### Account Registration and Verification
- Issues **6-digit OTP codes** by email using HTML templates (`emails/otp_verification.html`)
- Stages the new user temporarily, valid for 10 minutes
- Returns a Django REST Framework auth token once the account is verified

### Password Recovery
- OTP storage with a **5-minute expiry**
- Styled reset emails (`emails/password_reset_otp.html`)
- Issues a **single-use UUID reset token** after OTP verification
- Updates the password in the local database and Supabase, and records the change in `PasswordChangeHistory`

### Notification Emails
- Signal-based email on user registration (`api/signals.py`)
- A trigger endpoint (`/api/trigger-email/`) for project uploads, user approvals, and custom notifications
- Separate SMTP configurations for OTP emails and for signal-driven notifications

### Operations
- Configuration through environment variables (CORS, allowed hosts, Supabase buckets, SMTP)
- Health check endpoint (`/health`) for uptime monitoring

---

## 🧰 Tech Stack

- **Framework:** Django 5.x, Django REST Framework
- **Database:** PostgreSQL via `dj-database-url` and Supabase (SQLite for local development)
- **Email:** Python SMTP with a custom multi-backend (`SignalEmailBackend`)
- **Static files:** WhiteNoise
- **Serving:** Vercel serverless WSGI (Gunicorn on Render or Heroku also supported)

---

<details>
<summary><b>📋 API Reference (click to expand)</b></summary>

### Signup
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/signup/` | Register a user and email a 6-digit OTP |
| `POST` | `/api/verify-otp/` | Verify the signup OTP, activate the account, return an auth token |
| `POST` | `/api/resend-otp/` | Send a fresh OTP (`type`: `"signup"` or `"forgot_password"`) |

### Password Recovery
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/forgot-password/` | Check the user exists and send a 5-minute reset OTP |
| `POST` | `/api/verify-reset-otp/` | Verify the reset OTP and return a single-use `reset_token` |
| `POST` | `/api/verify-forgot-otp/` | Alias for `/api/verify-reset-otp/` |
| `POST` | `/api/reset-password/` | Set a new password using `reset_token`, sync Supabase, log history |

### Notifications
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/send-message/` | Send a custom subject and message to a recipient or admin |
| `POST` | `/api/trigger-email/` | Template emails: `welcome`, `admin_user_creation`, `admin_project_upload`, `feedback_approved`, `custom` |

### Health
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` or `/health/` | Service status |

</details>

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and fill in your own values. **Never commit your real `.env` file.**

```bash
cp .env.example .env
```

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,.vercel.app

# Database
DATABASE_URL=postgresql://user:password@your-db-host:6543/postgres

# SMTP for OTP emails (Gmail app password, not your normal password)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-character-app-password
DEFAULT_FROM_EMAIL=CADverse <your-email@gmail.com>
ADMIN_NOTIFICATION_EMAIL=your-email@gmail.com

# SMTP for signal and trigger emails
SIGNAL_EMAIL_HOST=smtp.gmail.com
SIGNAL_EMAIL_PORT=587
SIGNAL_EMAIL_USE_TLS=True
SIGNAL_EMAIL_HOST_USER=your-email@gmail.com
SIGNAL_EMAIL_HOST_PASSWORD=your-16-character-app-password
SIGNAL_DEFAULT_FROM_EMAIL=CADverse Notifications <your-email@gmail.com>

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_KEY=your-supabase-service-role-key
SUPABASE_BUCKET=your-files-bucket
SUPABASE_BUCKET_BEFORE=showcase-before
SUPABASE_BUCKET_AFTER=showcase-after

# CORS
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app,http://localhost:5173
```

---

## 💻 Local Development

```bash
# 1. Clone
git clone https://github.com/s-akhil-08/otp-email-service.git
cd otp-email-service

# 2. Virtual environment
python -m venv venv
source venv/bin/activate          # Windows: .\venv\Scripts\Activate.ps1

# 3. Install
pip install -r requirements.txt

# 4. Configure
cp .env.example .env              # then edit .env

# 5. Migrate and run
python manage.py migrate
python manage.py runserver 8000
```

Check it works at `http://127.0.0.1:8000/health/`:

```json
{
  "status": "healthy",
  "service": "CADverse OTP & Auth Microservice",
  "version": "1.0.0"
}
```

---

## 🚢 Deployment on Vercel

Recommended for this service.

1. Push the repo to GitHub and import it in [Vercel](https://vercel.com).
2. Make sure `vercel.json` points to `otp_service/wsgi.py` (it is included in this repo).
3. Add every variable from `.env.example` under **Project Settings → Environment Variables**.
4. Use a shared OTP store (database table or Redis) instead of `LocMemCache`, because each serverless request can run on a different instance.
5. Deploy, then open `/health/` on your Vercel URL to confirm.
6. Add the Vercel URL to the CORS list of the frontend and to the frontend's environment variables.

### Alternative: Render, Heroku, or containers

The `Procfile` is already set up:

```text
web: gunicorn otp_service.wsgi:application
```

Build command:

```bash
pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --no-input
```

On a single long-running server, `LocMemCache` is fine, but use one Gunicorn worker or a shared cache.

---

## 🔒 Security Notes

- Secrets live only in environment variables, and `.env` is git-ignored.
- OTPs expire (10 minutes for signup, 5 minutes for password reset).
- Password reset tokens are single-use.
- Use a **Gmail app password**, never your account password.
- Limit OTP requests and verification attempts per email or IP to prevent abuse.

---

## 📄 License

Licensed under the [MIT License](LICENSE).