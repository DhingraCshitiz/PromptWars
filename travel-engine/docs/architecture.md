# Travel Engine Architecture

## Overview
This document outlines the architecture for the Travel Planning and Experience Engine.

## Backend
- **Framework**: FastAPI (Python 3.12)
- **Database**: PostgreSQL (Cloud SQL) via SQLAlchemy and asyncpg.
- **Cache**: Redis for Google API response caching.
- **Async Jobs**: Cloud Tasks or background tasks for Gemini AI calls and re-planning events.
- **AI Integration**: Vertex AI Gemini for creating personalized itineraries.

## Frontend
- **Framework**: Angular
- **UI Toolkit**: Angular Material
- **State Management**: RxJS

## Google Cloud Infrastructure
- **Cloud Run**: Serverless backend hosting, scaling automatically.
- **Firebase Hosting**: Fast, secure hosting for the Angular application.
- **Cloud SQL**: Managed PostgreSQL database.
- **Firestore**: Real-time collaborative syncing for trips.
- **Secret Manager**: Storing DB passwords and API keys securely.

## Security Model
- **Authentication**: Firebase Auth (JWT validated by backend).
- **Network**: Backend accepts requests from Firebase Hosting origin. DB restricted to Cloud Run service account.
- **Secrets**: Handled by GCP Secret Manager, exposed to Cloud Run via env vars.
