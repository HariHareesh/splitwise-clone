# BUILD_PLAN.md
> Build plan for the Splitwise Clone internship assignment.
> Generated after full interview. No assumptions made — all decisions came from interview.

---

## 1. Product Research

### How Splitwise Was Studied
- Used regularly as an end user (trip splits, household bills)
- Reverse engineered core flows: group creation, expense entry, balance view, settle up
- Identified the debt simplification algorithm as the key differentiator

### Workflows Identified
1. **Onboarding**: Register → verify → land on dashboard
2. **Group setup**: Create group → invite members (3 methods) → members join
3. **Expense creation**: Pick group → add expense → choose split type → assign payers → save
4. **Balance check**: View group balances → see who owes whom → simplified transactions shown
5. **Settlement**: Tap "Settle up" → choose manual or online → record/pay → balance updates
6. **Chat**: Open expense or group → real-time chat with members

### Product Assumptions Made
- Currency is INR by default (single currency per group for MVP)
- Admin = group creator by default; admin can promote others
- Deleted expenses are hidden from balance calculations
- Settlement records are permanent (not soft-deleted)

---

## 2. Architecture

### Tech Stack
| Layer | Technology |
|---|---|
| Mobile | React Native (Expo SDK), Expo Router |
| State | Zustand |
| HTTP | Axios + JWT interceptor |
| Real-time | Native WebSocket API (Django Channels backend) |
| Backend | Django 4.x + Django REST Framework |
| ASGI | Daphne |
| WebSockets | Django Channels + Redis |
| Auth | SimpleJWT + django-allauth (Google OAuth) |
| Database | MySQL 8.x on AWS RDS |
| ORM | Django ORM |
| Email | AWS SES (boto3) |
| Push | Expo Push Notification Service |
| Payments | Razorpay (test mode) |
| Storage | AWS S3 (avatars, receipts) |
| Deployment | AWS EC2 (t3.small) + Nginx + Gunicorn/Daphne |
| Mobile Build | EAS Build (APK for Android, IPA for iOS) |

### Database Schema Summary
12 tables: `users`, `groups`, `group_members`, `expenses`, `expense_payers`,
`expense_splits`, `settlements`, `messages`, `notifications`, `group_invites`

Full schema in AI_CONTEXT.md Section 5.

### Debt Simplification Algorithm
```
1. Compute net[user] = sum(paid) - sum(owed) for each user in group
2. Subtract already-settled amounts from net
3. Separate into creditors (net > 0) and debtors (net < 0)
4. Sort both descending by absolute value
5. While debtors exist:
   a. Take largest debtor D and largest creditor C
   b. transfer = min(|D.net|, C.net)
   c. Record: D pays C → transfer amount
   d. Update D.net += transfer; C.net -= transfer
   e. Remove zeroed entries
6. Return list of (payer, payee, amount) transactions
```

### API Design Summary
- 6 auth endpoints
- 3 user endpoints
- 11 group endpoints (including balance, invite, join)
- 5 expense endpoints
- 4 settlement endpoints (including Razorpay initiate + verify)
- 2 REST chat endpoints + 2 WebSocket channels
- 3 notification endpoints

Full API design in AI_CONTEXT.md Section 7.

### Frontend Structure
Expo Router file-based navigation:
```
(auth)/         login, register, google-callback
(app)/          dashboard
  groups/       list, create, [id] detail, members, chat, balances, settle
    expenses/   create, [expenseId] detail + chat
  notifications/
  profile/
```

### Deployment Approach
- EC2 t3.small (Ubuntu 22.04): Django + Daphne (ASGI) behind Nginx
- RDS db.t3.micro: MySQL 8.x
- Redis on EC2 (same instance, port 6379)
- SSL via Certbot / Let's Encrypt
- EAS Build for APK/IPA — APK download link = "public deployed app URL"

---

## 3. AI Collaboration Process

### How the AI Was Instructed
- Pasted the required initial prompt from the assignment
- AI played junior engineer role: asked questions, did not assume, did not recommend
- Interview conducted in 7 structured rounds

### Questions Asked (by Round)
| Round | Topics Covered |
|---|---|
| 1 | Splitwise usage, dev experience, stack preference |
| 2 | Stack confirmation (frontend, backend, DB, real-time, deployment) |
| 3 | Auth method, group invite method, role-based access |
| 4 | Expense location, payer model, balance calculation method |
| 5 | Settlement method, chat scope, navigation flow |
| 6 | Expense deletion, notifications, UI form factor |
| 7 | Exact mobile framework, DB choice, backend framework, deployment targets |

### How the Plan Evolved
- Started with open questions; each answer locked in a decision
- No code was written until interview was complete
- AI_CONTEXT.md was produced after all decisions were confirmed
- BUILD_PLAN.md produced immediately after AI_CONTEXT.md

### How AI_CONTEXT.md Is Maintained
- Updated after every significant implementation decision
- Section 13 ("Changes During Implementation") tracks runtime changes
- Any schema change, API change, or logic change is logged there

---

## 4. Tradeoffs

### What Was Simplified
- Single currency per group (INR default) — no multi-currency
- No recurring expenses
- No expense categories or tags
- No activity/audit log UI
- Redis co-hosted on EC2 (not ElastiCache) to save cost

### What Was Hardcoded
- Default currency: INR
- Token expiry: access 1h, refresh 7d
- Invite link expiry: 7 days
- Max group members: no hard limit (DB constraint only)

### What Was Avoided
- Friend-level (non-group) expenses
- Cross-group debt simplification
- Real payment processing (Razorpay test mode only)
- Web app (mobile APK only)
- Admin UI for hard-deleting or restoring expenses

### What Would Be Improved With More Time
- Cross-group balance rollup on dashboard
- Expense categories + charts
- Push notification delivery receipts
- ElastiCache for Redis HA
- iOS TestFlight distribution
- Automated E2E tests (Detox)
- CI/CD pipeline (GitHub Actions → EC2 deploy)
- Multi-currency with live FX rates

---

## 5. Day-by-Day Build Schedule

### Day 1 — Backend
- [ ] Django project setup, settings, MySQL connection
- [ ] All models + migrations
- [ ] Auth: JWT + Google OAuth
- [ ] Groups API (CRUD + members + invite)
- [ ] Expenses API (CRUD + splits + payers)
- [ ] Balance calculation + debt simplification
- [ ] Settlements API + Razorpay integration
- [ ] Django Channels setup (WebSocket routing)
- [ ] Chat models + WebSocket consumers
- [ ] Notifications model + AWS SES email helper
- [ ] Deploy to EC2 + RDS + configure Nginx/Daphne

### Day 2 — Frontend
- [ ] Expo project setup, Expo Router, Zustand, Axios
- [ ] Auth screens (login, register, Google OAuth)
- [ ] Dashboard screen
- [ ] Groups list + create + detail screens
- [ ] Members management screen
- [ ] Expense create screen (all 4 split types)
- [ ] Expense detail screen
- [ ] Balance summary screen
- [ ] Settle up screen (manual + Razorpay)
- [ ] Group chat screen (WebSocket)
- [ ] Expense chat screen (WebSocket)
- [ ] Notifications screen
- [ ] Profile screen
- [ ] EAS Build → APK

### Day 3 — Polish & Deliverables
- [ ] Bug fixes from end-to-end testing
- [ ] README.md with setup instructions
- [ ] Finalize AI_CONTEXT.md
- [ ] Finalize BUILD_PLAN.md
- [ ] Collect all key prompts used → add to AI_CONTEXT.md Section 14
- [ ] Push to GitHub (public repo)
- [ ] Submit APK download link as deployed URL
