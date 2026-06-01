# Firebase Chatbot Lab

This project is a small lab app built with:

- Frontend: HTML, CSS, JavaScript
- Backend: FastAPI
- Authentication: Firebase Email/Password
- Database: Firestore

## Features

- Sign in and sign out with Firebase Authentication
- Show the current authenticated user
- Send a chat message from frontend to backend
- Verify Firebase ID token on the backend
- Save chat history to Firestore
- Load saved messages for the current user

## Project structure

```text
project/
|-- backend/
|   |-- main.py
|   |-- serviceAccountKey.example.json
|-- frontend/
|   |-- index.html
|   |-- style.css
|   |-- app.js
|   |-- firebase.js
|-- requirements.txt
|-- .gitignore
|-- README.MD
```

## Setup

1. Install dependencies:

```bash
py -m pip install -r requirements.txt
```

2. Create a Firebase project and enable:

- Authentication -> Email/Password
- Firestore Database

3. Download a Firebase Admin service account JSON file and place it at:

```text
backend/serviceAccountKey.json
```

You can also keep it elsewhere and set:

```bash
set FIREBASE_SERVICE_ACCOUNT_PATH=C:\path\to\serviceAccountKey.json
```

4. Update `frontend/firebase.js` with the Firebase Web App config from Firebase Console.

## Run

Start the backend:

```bash
cd backend
uvicorn main:app --reload
```

Start the frontend:

```bash
cd frontend
python -m http.server 5500
```

Open:

```text
http://127.0.0.1:5500
```

## API endpoints

- `GET /`
- `GET /health`
- `GET /auth/me`
- `POST /chat`
- `GET /messages`

All protected endpoints require:

```text
Authorization: Bearer <firebase_id_token>
```

## Notes

- The backend only returns messages for the authenticated user.
- Do not commit real Firebase service account files to Git.
- If you serve frontend from another port, update `CORS_ALLOW_ORIGINS` for the backend.
