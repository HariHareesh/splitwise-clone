# DECISIONS.md — Decision Log

## Decision 1: Tech Stack
**Options considered:**
- Django + MySQL (original stack)
- Django + PostgreSQL (Render free tier)
- FastAPI + PostgreSQL

**Decision:** Django + PostgreSQL (via Render free tier)

**Why:** Django was already set up. Render's free tier only offers PostgreSQL, not MySQL. Switching was straightforward using `dj-database-url`. FastAPI would have required a full rewrite.

---

## Decision 2: CSV Parsing Approach
**Options considered:**
- Parse CSV in frontend (JavaScript)
- Parse CSV in backend (Python/Django)
- Use a third-party service

**Decision:** Backend parsing in Django (Python)

**Why:** Python's `csv` module and `Decimal` library handle edge cases (commas in numbers, encoding issues) better than JavaScript. Backend parsing also keeps business logic server-side and makes the import report easy to return as JSON. Third-party services add unnecessary cost and dependency.

---

## Decision 3: Duplicate Detection Strategy
**Options considered:**
- Hash entire row
- Match on (date + amount + payer + description)
- Match on (date + amount + payer) only

**Decision:** Match on (date + amount + payer + description)

**Why:** Using all four fields reduces false positives. Two different expenses on the same day by the same person for the same amount but different descriptions should both be imported. Adding description makes the key more specific.

---

## Decision 4: Unknown Members Handling
**Options considered:**
- Auto-create new members
- Skip the row entirely
- Remove unknown member from split only

**Decision:** Remove unknown member from split; skip row if payer is unknown

**Why:** Unknown split members can be safely removed — the expense still happened, just the split changes. But an unknown payer means we can't record who paid, so the entire row must be skipped. Auto-creating members risks polluting the database with typos.

---

## Decision 5: Currency Handling
**Options considered:**
- Convert all to INR using live exchange rate
- Store original currency, flag USD entries
- Reject non-INR entries

**Decision:** Store original currency, flag USD/EUR entries in anomaly report

**Why:** We don't have a reliable exchange rate source or API key. Converting with a hardcoded rate would be inaccurate. Flagging lets the human reviewer decide. Rejecting would lose valid data.

---

## Decision 6: Date Format Ambiguity
**Options considered:**
- Reject ambiguous dates (e.g. "04/05/2026")
- Treat all DD/MM/YYYY (Indian convention)
- Treat all MM/DD/YYYY (US convention)

**Decision:** Treat as DD/MM/YYYY (Indian convention) and flag ambiguous dates

**Why:** The app is built for Indian users (INR default currency, Razorpay for payments). DD/MM/YYYY is the standard Indian date format. Flagging lets reviewers verify.

---

## Decision 7: Negative Amounts
**Options considered:**
- Treat as refund expense (negative split)
- Skip the row
- Convert to positive and import

**Decision:** Skip negative amount rows, flag as refund

**Why:** The expense model uses DECIMAL(10,2) which supports negatives, but a negative expense creates confusing balance calculations. Refunds should be modeled as settlements, not expenses. Flagging gives the reviewer context.

---

## Decision 8: Percentage Normalization
**Options considered:**
- Reject rows where percentages don't sum to 100%
- Normalize proportionally
- Use equal split as fallback

**Decision:** Normalize proportionally and flag

**Why:** Rejection loses valid data. Equal split ignores the intent. Proportional normalization preserves the relative weights the user intended while fixing the math error.

---

## Decision 9: Deployment Platform
**Options considered:**
- AWS EC2 + RDS (original plan)
- Render.com free tier
- Railway.app

**Decision:** Render.com free tier

**Why:** AWS EC2 requires credit card and has complex setup for a 3-day assignment. Render offers a free web service + free PostgreSQL database with GitHub auto-deploy. Railway had similar pricing but less documentation. Render was fastest to set up.

---

## Decision 10: Authentication for Import API
**Options considered:**
- Public endpoint (no auth)
- JWT authentication required
- API key authentication

**Decision:** JWT authentication required (IsAuthenticated)

**Why:** CSV files contain financial data. A public endpoint would be a security risk. JWT was already implemented for all other APIs, so reusing it was consistent and required zero extra code.
