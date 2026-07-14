# DepositBack

DepositBack is a full-stack app for managing rental deposits, leases, evidence, disputes, and generated documents. It includes a FastAPI backend and an Expo frontend.

## What It Does

- Stores properties, leases, and user profile data
- Manages evidence uploads and generated documents
- Supports deduction notices, claims, and dispute workflows
- Provides dashboard and preference endpoints for the app UI

## Tech Stack

- Backend: FastAPI, SQLAlchemy, Alembic, PostgreSQL
- Frontend: Expo, React Native, TypeScript
- Auth and storage: Supabase
- AI features: Google Gemini

## Project Structure

- `app/` - FastAPI backend code
- `alembic/` - database migrations
- `frontend/` - Expo mobile/web frontend
- `tests/` - automated tests

## Requirements

- Python for the backend
- Node.js for the frontend
- A PostgreSQL database
- Supabase and Gemini API credentials

## Backend Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with the required values from `app/core/config.py`.
4. The backend expects settings for the database, Supabase, Gemini, storage, and environment name.
5. Run database migrations:

```bash
alembic upgrade head
```

6. Start the backend:

```bash
uvicorn app.main:app --reload
```

The backend health check is available at `/health`, and the root route returns a simple running status.

## Frontend Setup

1. Go to the `frontend/` folder.
2. Install dependencies:

```bash
npm install
```

3. Start the app:

```bash
npm run start
```

You can also use `npm run android`, `npm run ios`, or `npm run web`.

## API Areas

- These are the main API prefixes registered in `app/main.py`.
- `/me` - user profile
- `/preferences` - user settings
- `/properties` - property management and dashboard data
- `/lease` - lease management
- `/evidence` - evidence uploads and tracking
- `/deduction-notices` - dispute notices
- `/claims` - claims flow
- `/generated-documents` - generated documents


