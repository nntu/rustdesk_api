# RustDesk API Server

## Project Overview

This project is a fully-featured API server for [RustDesk](https://rustdesk.com/), an open-source remote desktop software. It provides backend services for client authentication, device management, address book synchronization, and audit logging. It also includes a web-based administration interface.

**Tech Stack:**
*   **Framework:** Python 3.13+ / Django 5.2
*   **Server:** Gunicorn (WSGI)
*   **Database:** SQLite (default), MySQL, or PostgreSQL
*   **Static Files:** WhiteNoise

## Architecture & Structure

The project follows a modular Django application structure, organizing functionality into distinct apps within the `apps/` directory.

*   **`apps/client_apis/`**: Handles API requests from the RustDesk client (login, heartbeat, sysinfo).
*   **`apps/web/`**: Views for the web-based management dashboard.
*   **`apps/db/`**: Contains database models (`models.py`) and business logic/services (`service.py`).
*   **`apps/commands/`**: Custom Django management commands.
*   **`apps/common/`**: Shared middleware and utilities.
*   **`rustdesk_api/`**: Main project configuration (`settings.py`, `urls.py`, `wsgi.py`).
*   **`common/`**: System-wide configuration helpers (environment variables, logging, database config).

## Key Files

*   **`rustdesk_api/settings.py`**: Main Django settings. Loads configuration from environment variables via `common.env`.
*   **`apps/client_apis/urls.py`**: Defines the routing for the client-facing API (e.g., `/api/client/login`, `/api/client/heartbeat`).
*   **`requirements.txt`**: Python dependencies.
*   **`docker/docker-compose.yml`**: Definition for running the service in Docker.
*   **`manage.py`**: Django's command-line utility for administrative tasks.

## Building and Running

### Docker (Recommended)

To start the server with Docker Compose:

```bash
docker-compose up -d
```
Access the API at `http://localhost:21114` and the web admin at `http://localhost:21114/web/`.

### Manual Development Setup

1.  **Environment Setup:**
    Create a virtual environment and install dependencies:
    ```bash
    python -m venv venv
    # Windows: venv\Scripts\activate
    # Linux/Mac: source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Configuration:**
    Set environment variables if needed (defaults to SQLite and DEBUG=False).
    For development:
    ```bash
    export DEBUG=True
    ```

3.  **Database Initialization:**
    ```bash
    python manage.py migrate
    python manage.py createsuperuser
    ```

4.  **Running the Server:**
    ```bash
    python manage.py runserver 0.0.0.0:21114
    ```

## Configuration

The application is configured primarily through environment variables. Key variables include:

*   `DATABASE`: `sqlite3` (default), `mysql`, or `postgresql`.
*   `DEBUG`: `True` or `False`.
*   `SECRET_KEY`: Django secret key.
*   `WORKERS` / `THREADS`: Gunicorn worker configuration.
*   `SESSION_TIMEOUT`: Session duration in seconds.

See `README_EN.md` for a complete list of environment variables and database-specific configurations.

## Development Conventions

*   **App Separation:** Keep distinct functionality in separate apps under `apps/`.
*   **Settings:** Do not hardcode secrets or environment-specific settings in `settings.py`. Use the `PublicConfig` class in `common/env.py` to retrieve them.
*   **Static Files:** `collectstatic` must be run for production deployment as `whitenoise` is used to serve them.
