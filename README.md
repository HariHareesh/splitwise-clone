# Splitwise Clone

A simplified Splitwise-inspired expense splitting app built with Django + React Native (Expo).

## AI Tool Used
Claude (Anthropic) — claude.ai

## Deployed URLs
- **Backend API**: https://splitwise-clone-imds.onrender.com
- **Mobile App (APK)**: https://expo.dev/artifacts/eas/DHdaNjfO0-mESZgVgaysSba2pIBDuRGbLmPja7dn6aE.apk

## GitHub Repository
https://github.com/HariHareesh/splitwise-clone

## Tech Stack
| Layer | Technology |
|---|---|
| Mobile Frontend | React Native (Expo SDK 56) |
| Backend | Django 6.0 + Django REST Framework |
| Real-time | Django Channels + WebSockets |
| Database | PostgreSQL (Render) |
| Auth | JWT (SimpleJWT) + Google OAuth |
| Deployment | Render.com (Backend) + EAS Build (APK) |

## Features
- ✅ Email + Password Login & Registration
- ✅ Google OAuth
- ✅ Create and manage groups (admin/member roles)
- ✅ Invite users by email, username search, or invite link
- ✅ Create expenses with 4 split types (equal, unequal, percentage, share)
- ✅ Multiple payers per expense
- ✅ Group-wise balance summary
- ✅ Debt simplification algorithm (minimum transactions)
- ✅ Settle debts manually or online (Razorpay)
- ✅ Real-time chat per group and per expense (WebSockets)
- ✅ In-app notifications
- ✅ Soft delete for expenses

## Setup Instructions

### Backend Setup
```bash
# Clone the repo
git clone https://github.com/HariHareesh/splitwise-clone.git
cd splitwise-clone

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Fill in your DB credentials

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver 0.0.0.0:8000
```

### Frontend Setup
```bash
cd splitwise-app

# Install dependencies
npm install

# Update API URL in constants/api.ts
# Change API_BASE_URL to your backend URL

# Run on Expo Go
npx expo start

# Build APK
eas build --platform android --profile preview
```

### Environment Variables (.env)
```
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=*
DB_NAME=splitwise_db
DB_USER=root
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=3306
REDIS_HOST=127.0.0.1
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
```

## Database Schema
See AI_CONTEXT.md for full database schema.

## API Documentation
See AI_CONTEXT.md for full API design.