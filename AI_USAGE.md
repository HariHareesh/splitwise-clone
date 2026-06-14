# AI_USAGE.md — AI Tools Used

## Tools Used
- **Claude (Anthropic)** — Primary AI assistant for architecture, code generation, debugging
- **OpenAI Codex** — UI polish for React Native screens

---

## Key Prompts Used

### 1. Initial Architecture Interview
> "You are a junior engineer helping me complete an internship assignment. The assignment is to reverse engineer Splitwise, scope a realistic 3-day version, and build a working deployed app..."

Used to scope the entire project through a structured interview before writing any code.

### 2. Django Models Generation
> "Create Django models for groups, expenses with 4 split types (equal, unequal, percentage, share), settlements, chat messages, and notifications"

Generated all 6 app models with correct ForeignKey relationships and field types.

### 3. Debt Simplification Algorithm
> "Implement the Splitwise debt simplification algorithm — fewest transactions to settle all debts in a group"

Generated the min-cash-flow algorithm using a greedy approach.

### 4. CSV Import Logic
> "Write a Django REST API view that accepts a CSV file, detects anomalies (duplicates, bad dates, unknown members, wrong percentages), and returns a JSON import report"

Generated the full `ImportCSVView` with 9 anomaly detection rules.

### 5. UI Polish (Codex)
> "You are a senior React Native UI/UX engineer. Polish my Splitwise clone app completely. Tech stack: React Native + Expo SDK 56..."

Used to improve login, register, dashboard, and group detail screens.

---

## Cases Where AI Produced Something Wrong

### Case 1: Wrong INSTALLED_APPS Order (Django)
**What AI did:** Generated `settings.py` with `daphne` inside `THIRD_PARTY_APPS`, after `django.contrib.staticfiles`.

**Error:** `daphne.E001 — Daphne must be listed before django.contrib.staticfiles`

**How I caught it:** Running `python manage.py makemigrations` threw a `SystemCheckError`.

**What I changed:** Manually moved `'daphne'` to the top of `DJANGO_APPS` list, before all other Django apps. AI had not accounted for Daphne's strict ordering requirement.

---

### Case 2: Wrong Import Paths in React Native (Dashboard)
**What AI (Codex) did:** Generated `dashboard.tsx` with import paths `../../../stores/api` and `../../../stores/authStore`.

**Error:** `Unable to resolve module ../../../stores/api from app/(app)/dashboard.tsx`

**How I caught it:** EAS Build failed at the "Bundle JavaScript" phase with a module resolution error.

**What I changed:** Corrected the paths to `../../stores/api` and `../../stores/authStore` because `dashboard.tsx` is at depth `app/(app)/`, not `app/(app)/groups/[id]/`, so only two levels of `../` are needed, not three.

---

### Case 3: LinearGradient Import Without Installing Package
**What AI (Codex) did:** Added `import { LinearGradient } from 'expo-linear-gradient'` to `groups/[id].tsx` without checking if the package was installed.

**Error:** `expo-linear-gradient could not be found within the project`

**How I caught it:** EAS Build failed. Checked `package.json` — package was listed but not actually installed in `node_modules` because `npm install` hadn't been re-run after Codex added it.

**What I changed:** Ran `npx expo install expo-linear-gradient` to properly install it. Also added `.npmrc` with `legacy-peer-deps=true` to fix peer dependency conflicts on the EAS build server.

---

### Case 4: MySQL vs PostgreSQL Mismatch on Render
**What AI did:** Generated `settings.py` configured for MySQL (`django.db.backends.mysql`) and instructed to add MySQL environment variables to Render.

**Error:** Render free tier does not support MySQL — only PostgreSQL is available for free.

**How I caught it:** Backend deployed but returned 500 errors on all API calls. Render logs showed `django.db.backends.mysql` trying to connect to `localhost` which doesn't exist on Render.

**What I changed:** Installed `psycopg2-binary` and `dj-database-url`, rewrote the `DATABASES` setting to use `DATABASE_URL` environment variable (PostgreSQL), and created a free Render PostgreSQL database. Updated `requirements.txt` and redeployed.

---

### Case 5: Percentage Validation Logic Error
**What AI did:** In the CSV import view, generated percentage validation that checked `if total != 100` using float comparison.

**Error:** `Decimal('99.9999999')` was being flagged as invalid due to floating point precision issues.

**How I caught it:** Tested with a row where percentages were `33.33, 33.33, 33.34` — these summed to exactly 100 but float comparison flagged them.

**What I changed:** Replaced `!=` with `abs(total - 100) > Decimal('0.01')` to allow for minor rounding tolerance, and switched all calculations to use Python's `Decimal` type instead of `float` for accurate financial math.
