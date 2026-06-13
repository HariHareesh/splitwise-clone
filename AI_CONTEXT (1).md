# AI_CONTEXT.md
> Source of truth for the Splitwise Clone internship assignment.
> Maintained continuously. Another developer or AI agent should be able to rebuild this app from this file alone.

---

## 1. Product Understanding

Splitwise is an expense-sharing app that lets groups of people track shared costs, calculate who owes whom, and settle debts. Core value: eliminating the awkwardness of money among friends/roommates/colleagues.

Key behaviours studied:
- Groups are the primary container for expenses
- Expenses can be split in multiple ways (equal, unequal, percentage, share)
- Balances are simplified — Splitwise computes the minimum number of transactions to settle all debts
- Payments can be recorded manually or made online
- Real-time chat exists both at expense level and group level
- Users are notified in-app and via email on key events

---

## 2. Product Scope (MVP)

### In Scope
- Email + password login AND Google OAuth
- Group creation with role-based access (admin vs member)
- Invite users by email, username search, or shareable invite link
- Only admins can add/remove members
- Expenses only within groups (no 1:1 friend expenses)
- Expense split types: equal, unequal, by percentage, by share
- Multiple payers per expense supported
- Soft delete for expenses (hidden, recoverable)
- Real-time chat per expense AND per group
- Group-wise balance summary + individual balance summary
- Settle debts: record manually OR pay online (payment gateway)
- Debt simplification algorithm (minimum transactions)
- In-app notifications + email notifications
- Mobile app: React Native (Expo) → EAS Build (APK/IPA)

### Out of Scope
- Friend-level (non-group) expenses
- Currency conversion
- Recurring expenses
- Expense categories/tags (nice to have, not required)
- Activity log / audit trail (beyond basic balance history)
- Web app (mobile only)

---

## 3. User Personas

- **Primary**: Young adults splitting rent, trips, household bills
- **Roles inside app**:
  - `admin` — group creator or promoted member; can add/remove members, edit group settings
  - `member` — can create expenses, chat, view balances, settle debts

---

## 4. Tech Stack

| Layer | Choice |
|---|---|
| Mobile Frontend | React Native (Expo SDK) |
| Backend | Django (Python) + Django REST Framework |
| Real-time | Django Channels + Redis (WebSockets) |
| Database | MySQL on AWS RDS |
| Auth | JWT (SimpleJWT) + Google OAuth (via django-allauth) |
| Push Notifications | Expo Push Notification Service |
| Email Notifications | AWS SES |
| Payment Gateway | Razorpay (or Stripe — TBD) |
| Backend Deployment | AWS EC2 (Django) + AWS RDS (MySQL) |
| Mobile Deployment | EAS Build → standalone APK/IPA |
| File/Media Storage | AWS S3 (profile pictures, receipts) |
| WebSocket Layer | Django Channels backed by Redis (AWS ElastiCache or EC2-hosted Redis) |

---

## 5. Database Schema

### `users`
```
id            INT PK AUTO_INCREMENT
email         VARCHAR(255) UNIQUE NOT NULL
username      VARCHAR(100) UNIQUE NOT NULL
password_hash VARCHAR(255)                  -- null if OAuth only
google_id     VARCHAR(255) UNIQUE
full_name     VARCHAR(255)
avatar_url    VARCHAR(500)
expo_push_token VARCHAR(255)
created_at    DATETIME
updated_at    DATETIME
is_active     BOOLEAN DEFAULT TRUE
```

### `groups`
```
id            INT PK AUTO_INCREMENT
name          VARCHAR(255) NOT NULL
description   TEXT
avatar_url    VARCHAR(500)
invite_token  VARCHAR(64) UNIQUE            -- for shareable invite link
created_by    INT FK → users.id
created_at    DATETIME
updated_at    DATETIME
is_active     BOOLEAN DEFAULT TRUE
```

### `group_members`
```
id            INT PK AUTO_INCREMENT
group_id      INT FK → groups.id
user_id       INT FK → users.id
role          ENUM('admin','member') DEFAULT 'member'
joined_at     DATETIME
is_active     BOOLEAN DEFAULT TRUE
UNIQUE(group_id, user_id)
```

### `expenses`
```
id            INT PK AUTO_INCREMENT
group_id      INT FK → groups.id
title         VARCHAR(255) NOT NULL
total_amount  DECIMAL(12,2) NOT NULL
currency      VARCHAR(10) DEFAULT 'INR'
split_type    ENUM('equal','unequal','percentage','share') NOT NULL
created_by    INT FK → users.id
created_at    DATETIME
updated_at    DATETIME
deleted_at    DATETIME                      -- soft delete
is_deleted    BOOLEAN DEFAULT FALSE
notes         TEXT
receipt_url   VARCHAR(500)
```

### `expense_payers`
```
id            INT PK AUTO_INCREMENT
expense_id    INT FK → expenses.id
user_id       INT FK → users.id
amount_paid   DECIMAL(12,2) NOT NULL
```

### `expense_splits`
```
id            INT PK AUTO_INCREMENT
expense_id    INT FK → expenses.id
user_id       INT FK → users.id
owed_amount   DECIMAL(12,2) NOT NULL        -- final computed amount this user owes
split_value   DECIMAL(12,4)                 -- raw input: share count / percentage / exact amount
```

### `settlements`
```
id            INT PK AUTO_INCREMENT
group_id      INT FK → groups.id
payer_id      INT FK → users.id            -- person paying
payee_id      INT FK → users.id            -- person receiving
amount        DECIMAL(12,2) NOT NULL
method        ENUM('manual','online') NOT NULL
payment_ref   VARCHAR(255)                  -- gateway txn ID if online
status        ENUM('pending','completed') DEFAULT 'completed'
settled_at    DATETIME
created_at    DATETIME
```

### `messages`
```
id            INT PK AUTO_INCREMENT
group_id      INT FK → groups.id           -- null if expense-level
expense_id    INT FK → expenses.id         -- null if group-level
sender_id     INT FK → users.id
content       TEXT NOT NULL
created_at    DATETIME
is_deleted    BOOLEAN DEFAULT FALSE
```

### `notifications`
```
id            INT PK AUTO_INCREMENT
user_id       INT FK → users.id
type          VARCHAR(100)                  -- e.g. 'expense_added', 'group_invite', 'settlement'
title         VARCHAR(255)
body          TEXT
is_read       BOOLEAN DEFAULT FALSE
meta_json     JSON                          -- extra context (group_id, expense_id, etc.)
created_at    DATETIME
```

### `group_invites`
```
id            INT PK AUTO_INCREMENT
group_id      INT FK → groups.id
invited_by    INT FK → users.id
email         VARCHAR(255)                  -- for email invites
token         VARCHAR(64) UNIQUE            -- for link invites
status        ENUM('pending','accepted','expired') DEFAULT 'pending'
created_at    DATETIME
expires_at    DATETIME
```

---

## 6. Balance Calculation Logic

1. For each group, compute net balance per user:
   - Sum all `expense_payers.amount_paid` for user → total paid
   - Sum all `expense_splits.owed_amount` for user → total owed
   - Net = total_paid − total_owed
2. Users with positive net are owed money (creditors).
3. Users with negative net owe money (debtors).
4. Apply **debt simplification**: greedy two-pointer algorithm — match largest debtor with largest creditor, record a settlement transaction, repeat until all balances are zero.
5. Subtract already-recorded settlements from net balances before simplification.

---

## 7. API Design

### Auth
```
POST   /api/auth/register/
POST   /api/auth/login/
POST   /api/auth/google/
POST   /api/auth/token/refresh/
POST   /api/auth/logout/
```

### Users
```
GET    /api/users/me/
PUT    /api/users/me/
GET    /api/users/search/?q=username
```

### Groups
```
GET    /api/groups/
POST   /api/groups/
GET    /api/groups/{id}/
PUT    /api/groups/{id}/
DELETE /api/groups/{id}/
GET    /api/groups/{id}/members/
POST   /api/groups/{id}/members/
DELETE /api/groups/{id}/members/{user_id}/
POST   /api/groups/{id}/invite/          -- send email invite
GET    /api/groups/join/{token}/          -- accept invite link
GET    /api/groups/{id}/balances/         -- group-wise balance summary
GET    /api/groups/{id}/my-balance/       -- current user's net in group
```

### Expenses
```
GET    /api/groups/{id}/expenses/
POST   /api/groups/{id}/expenses/
GET    /api/expenses/{id}/
PUT    /api/expenses/{id}/
DELETE /api/expenses/{id}/               -- soft delete
GET    /api/expenses/{id}/splits/
```

### Settlements
```
GET    /api/groups/{id}/settlements/
POST   /api/groups/{id}/settlements/
POST   /api/groups/{id}/settlements/initiate-payment/   -- Razorpay order
POST   /api/groups/{id}/settlements/verify-payment/     -- webhook / callback
```

### Chat (REST fallback + WebSocket primary)
```
GET    /api/groups/{id}/messages/
GET    /api/expenses/{id}/messages/

WS     ws://host/ws/group/{id}/
WS     ws://host/ws/expense/{id}/
```

### Notifications
```
GET    /api/notifications/
PUT    /api/notifications/{id}/read/
PUT    /api/notifications/read-all/
```

---

## 8. Frontend Structure (React Native / Expo)

```
app/
├── (auth)/
│   ├── login.tsx
│   ├── register.tsx
│   └── google-callback.tsx
├── (app)/
│   ├── dashboard.tsx              -- home: list of groups + overall balance
│   ├── groups/
│   │   ├── index.tsx              -- all groups
│   │   ├── create.tsx
│   │   └── [id]/
│   │       ├── index.tsx          -- group detail: expenses + balance summary
│   │       ├── members.tsx
│   │       ├── chat.tsx           -- group-level chat
│   │       ├── balances.tsx
│   │       ├── settle.tsx
│   │       └── expenses/
│   │           ├── create.tsx
│   │           └── [expenseId]/
│   │               ├── index.tsx  -- expense detail + split breakdown
│   │               └── chat.tsx   -- expense-level chat
│   ├── notifications.tsx
│   └── profile.tsx
├── _layout.tsx
└── index.tsx
```

State management: Zustand (lightweight, no boilerplate)
API calls: Axios with JWT interceptor (auto-refresh)
WebSocket: native WebSocket API wrapped in a custom hook
Navigation: Expo Router (file-based)

---

## 9. Deployment Plan

### Backend (AWS EC2)
- Ubuntu 22.04 t3.small EC2
- Gunicorn + Nginx (reverse proxy)
- Django Channels via Daphne (ASGI server)
- Redis on same EC2 (or ElastiCache)
- MySQL on AWS RDS (db.t3.micro)
- SSL via Let's Encrypt (Certbot)
- Environment variables via `.env` + EC2 parameter store
- Domain: subdomain pointing to EC2 Elastic IP

### Mobile (EAS Build)
- `eas build --platform android` → APK
- `eas build --platform ios` → IPA (requires Apple Developer account)
- Distribute APK via direct download link in README
- Expo updates for OTA patches

---

## 10. Testing Plan

- **Unit tests**: Django `TestCase` for balance calculation logic, split type computations
- **API tests**: DRF `APITestCase` for all endpoints (auth, groups, expenses, settlements)
- **Manual testing**: Expo Go during development, then EAS build for final
- **WebSocket testing**: manual test with two devices on same group/expense chat

---

## 11. Known Tradeoffs & Limitations

| Decision | Tradeoff |
|---|---|
| MySQL over PostgreSQL | Assignment allows it; Django ORM works fine. Less native JSON support but using JSON field for notification meta. |
| Debt simplification is group-scoped | Cross-group simplification (like Splitwise Pro) is out of scope |
| Redis on same EC2 as Django | Cost saving; not production-grade HA but fine for demo |
| No recurring expenses | Out of scope for 2-day build |
| EAS build (not web) | No public browser URL — APK download link used as "deployed URL" |
| Payment gateway (Razorpay) | Real payments need KYC; test mode used for demo |
| Email via AWS SES | SES sandbox requires verified recipient emails in test |
| Soft delete only | No admin UI to hard-delete or restore yet |

---

## 12. AI Collaboration Log

### Interview Summary
Questions asked across: product goals, Splitwise usage, stack, auth, groups, expenses, splits, balances, settlements, chat, UI, deployment, notifications, edge cases.

### Key Decisions Made During Interview
- Auth: Email+password AND Google OAuth
- Groups: Role-based (admin/member); invite by email, username search, or link
- Expenses: Group-only; multiple payers supported; 4 split types
- Balances: Debt simplification (minimum transactions)
- Settlement: Record manually OR pay online (Razorpay)
- Chat: Both expense-level and group-level, real-time via WebSockets
- Soft delete for expenses
- Notifications: In-app + email (AWS SES)
- Mobile: React Native Expo → EAS Build APK/IPA
- Backend: Django + DRF + Django Channels
- DB: MySQL on AWS RDS
- Deployment: AWS EC2 + RDS

---

## 13. Changes During Implementation
> (To be updated as the build progresses)

---

## 14. Prompts Used
> Initial prompt per assignment instructions pasted into Claude.
> Interview conducted across 7 rounds covering all required decision areas.
> BUILD_PLAN.md generated after interview completion.
