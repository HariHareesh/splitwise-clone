# SCOPE.md — Anomaly Log & Database Schema

## Project Overview
CSV expense import feature for a Splitwise-clone app. The CSV (`expenses_export.csv`) contains shared house expense records for 5 members: Alice, Bob, Priya, Sam, Meera (and guest Kabir in one row).

---

## Anomalies Found in CSV

| # | Row | Anomaly Type | Description | Action Taken |
|---|-----|-------------|-------------|--------------|
| 1 | 4,5 | Duplicate entry | Same description "Marina Bites dinner", same date, same amount, same payer | Second entry skipped |
| 2 | 6 | Malformed amount | Amount stored as "1,200" with comma separator | Comma removed, parsed as 1200.00 |
| 3 | 8 | Name casing | Payer stored as "priya" (lowercase) | Normalized to "Priya" using .title() |
| 4 | 9 | Precision issue | Amount 899.995 has 3 decimal places | Rounded to 899.99 (2 decimal places) |
| 5 | 10 | Unknown payer | Payer listed as "Priya S" — not in known members list | Row skipped |
| 6 | 12 | Missing payer | paid_by field is blank | Row skipped |
| 7 | 13 | Settlement as expense | Description contains "settlement" — not a real expense | Row skipped |
| 8 | 14 | Percentages don't sum to 100% | Split percentages: 30+30+30+20 = 110% | Normalized proportionally to sum to 100% |
| 9 | Multiple | Mixed date formats | Dates in DD/MM/YYYY, YYYY-MM-DD, "Mar 14", "April 5" formats | All normalized to YYYY-MM-DD |
| 10 | Multiple | USD currency | Some expenses in USD instead of INR | Flagged in report, kept as-is (no conversion rate assumed) |
| 11 | 25 | Negative amount | Amount is -500 (refund) | Flagged as refund, skipped |
| 12 | 23,24 | Near-duplicate | "Thalassa dinner" appears twice with different amounts on same day | Both imported, flagged as possible duplicate |
| 13 | 27 | Missing currency | currency field is blank | Defaulted to INR, flagged |
| 14 | 30 | Zero amount | Amount is 0 | Skipped — zero-value expenses are meaningless |
| 15 | 33 | Ambiguous date | "04/05/2026" could be April 5 or May 4 | Treated as DD/MM/YYYY (May 4) per Indian convention |
| 16 | 35 | Member moved out | Meera included in April split after moving out in March | Flagged in report |
| 17 | 37 | Deposit as expense | Description: "Sam deposit" — a financial transfer, not expense | Skipped |
| 18 | 22 | Unknown split member | "Kabir" in split_among but not a house member | Removed from split, flagged |

---

## Database Schema

### Table: `import_sessions`
| Column | Type | Description |
|--------|------|-------------|
| id | INT PK | Auto increment |
| uploaded_by | FK → users | Who uploaded |
| filename | VARCHAR(255) | Original CSV filename |
| uploaded_at | DATETIME | Upload timestamp |
| total_rows | INT | Total rows in CSV |
| imported_count | INT | Successfully imported |
| skipped_count | INT | Skipped rows |
| anomaly_count | INT | Rows with anomalies |

### Table: `imported_expenses`
| Column | Type | Description |
|--------|------|-------------|
| id | INT PK | Auto increment |
| session | FK → import_sessions | Which import |
| row_number | INT | Original CSV row |
| description | VARCHAR(500) | Expense description |
| amount | DECIMAL(10,2) | Cleaned amount |
| currency | VARCHAR(3) | INR/USD/EUR |
| date | DATE | Normalized date |
| paid_by | VARCHAR(100) | Payer name |
| split_among | JSON | List of member names |
| split_type | VARCHAR(20) | equal/percentage/share |
| action | VARCHAR(20) | imported/skipped |
| anomalies | JSON | List of anomaly descriptions |
| created_at | DATETIME | Record creation time |

---

## How Anomalies Were Handled (Summary)

- **Duplicates** → Exact duplicates (same date + amount + payer + description) are skipped. Near-duplicates are flagged but imported.
- **Malformed amounts** → Commas removed, rounded to 2 decimal places, zero/negative amounts skipped.
- **Name normalization** → All names converted to Title Case and matched against known member list.
- **Unknown members** → Removed from split; if payer is unknown, row is skipped entirely.
- **Date normalization** → Multiple formats parsed and stored as YYYY-MM-DD.
- **Settlements/transfers** → Detected by keywords in description and skipped.
- **Missing fields** → Missing paid_by or amount → row skipped. Missing currency → defaulted to INR.
- **Percentage splits** → If percentages don't sum to 100%, they are normalized proportionally.
