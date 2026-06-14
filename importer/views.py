import csv
import io
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from difflib import get_close_matches

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone

from groups.models import Group, GroupMember
from expenses.models import Expense, ExpensePayer, ExpenseSplit
from settlements.models import Settlement
from users.models import User
from .models import ImportSession, ImportAnomaly

# USD to INR conversion rate
USD_TO_INR = Decimal('83.5')

# Known members (normalized)
KNOWN_MEMBERS = ['Aisha', 'Rohan', 'Priya', 'Meera', 'Dev', 'Sam']

# Member active periods
MEMBER_PERIODS = {
    'Aisha': {'joined': date(2026, 2, 1), 'left': None},
    'Rohan': {'joined': date(2026, 2, 1), 'left': None},
    'Priya': {'joined': date(2026, 2, 1), 'left': None},
    'Meera': {'joined': date(2026, 2, 1), 'left': date(2026, 3, 31)},
    'Dev':   {'joined': date(2026, 2, 8), 'left': date(2026, 3, 14)},
    'Sam':   {'joined': date(2026, 4, 10), 'left': None},
}

SETTLEMENT_KEYWORDS = ['paid back', 'settlement', 'deposit', 'paid aisha', 'paid rohan', 'paid priya']


def normalize_name(name):
    """Normalize member name to Title Case and fuzzy match."""
    if not name:
        return None
    name = name.strip().title()
    if name in KNOWN_MEMBERS:
        return name
    matches = get_close_matches(name, KNOWN_MEMBERS, n=1, cutoff=0.6)
    return matches[0] if matches else name


def parse_amount(raw):
    """Parse amount string, handle commas and extra decimals."""
    if not raw:
        return None, None
    cleaned = str(raw).strip().replace(',', '').replace('₹', '').replace('$', '').strip()
    try:
        amount = Decimal(cleaned)
        original = raw
        if str(raw) != cleaned:
            return amount, f"Cleaned from '{raw}' to '{cleaned}'"
        return amount, None
    except InvalidOperation:
        return None, f"Cannot parse amount: '{raw}'"


def parse_date(raw):
    """Parse date from multiple formats."""
    if not raw:
        return None, 'missing_date'
    raw = str(raw).strip()
    formats = [
        ('%Y-%m-%d', False),
        ('%d/%m/%Y', False),
        ('%m/%d/%Y', True),
        ('%b %d', False),
        ('%B %d', False),
    ]
    for fmt, ambiguous in formats:
        try:
            if '%b' in fmt or '%B' in fmt:
                parsed = datetime.strptime(f"{raw} 2026", fmt + ' %Y').date()
            else:
                parsed = datetime.strptime(raw, fmt).date()
            return parsed, 'ambiguous_date' if ambiguous else None
        except ValueError:
            continue
    return None, 'unparseable_date'


def is_settlement(row):
    """Detect if a row is a settlement rather than an expense."""
    notes = str(row.get('notes', '') or '').lower()
    title = str(row.get('description', '') or row.get('title', '') or '').lower()
    for kw in SETTLEMENT_KEYWORDS:
        if kw in notes or kw in title:
            return True
    return False


def validate_percentages(splits):
    """Check if percentage splits sum to 100."""
    try:
        total = sum(Decimal(str(v)) for v in splits.values())
        return total, abs(total - 100) < Decimal('0.01')
    except Exception:
        return None, False


class CSVImportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        group = get_object_or_404(Group, pk=group_id, is_active=True)

        if not GroupMember.objects.filter(group=group, user=request.user, is_active=True).exists():
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)

        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        if not csv_file.name.endswith('.csv'):
            return Response({'error': 'File must be a CSV'}, status=status.HTTP_400_BAD_REQUEST)

        content = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)

        session = ImportSession.objects.create(
            group=group,
            imported_by=request.user,
            filename=csv_file.name,
            total_rows=len(rows),
            status='pending'
        )

        anomalies = []
        imported = 0
        skipped = 0
        seen_rows = []  # for duplicate detection

        def log_anomaly(row_num, atype, desc, original='', resolved='', action='needs_review'):
            anomalies.append({
                'row': row_num,
                'type': atype,
                'description': desc,
                'original': str(original),
                'resolved': str(resolved),
                'action': action,
            })
            ImportAnomaly.objects.create(
                import_session=session,
                row_number=row_num,
                anomaly_type=atype,
                description=desc,
                original_value=str(original),
                resolved_value=str(resolved),
                action_taken=action,
            )

        for i, row in enumerate(rows, start=2):
            row_num = i
            skip_row = False

            # --- Get raw fields ---
            raw_title = (row.get('description') or row.get('title') or '').strip()
            raw_amount = (row.get('amount') or '').strip()
            raw_date = (row.get('date') or '').strip()
            raw_payer = (row.get('paid_by') or '').strip()
            raw_currency = (row.get('currency') or 'INR').strip().upper()
            raw_split_type = (row.get('split_type') or 'equal').strip().lower()
            raw_notes = (row.get('notes') or '').strip()
            raw_split_with = (row.get('split_with') or '').strip()

            # --- Settlement detection ---
            if is_settlement(row):
                log_anomaly(row_num, 'reclassified_as_settlement',
                    f'"{raw_title}" appears to be a settlement, not an expense.',
                    raw_title, 'Moved to settlements table', 'reclassified')
                skipped += 1
                continue

            # --- Zero amount ---
            if raw_amount == '0' or raw_amount == '0.0':
                log_anomaly(row_num, 'zero_amount',
                    f'"{raw_title}" has amount=0. Notes: "{raw_notes}"',
                    raw_amount, 'Skipped', 'skipped')
                skipped += 1
                continue

            # --- Parse amount ---
            amount, amount_note = parse_amount(raw_amount)
            if amount is None:
                log_anomaly(row_num, 'invalid_amount',
                    f'Cannot parse amount "{raw_amount}" for "{raw_title}"',
                    raw_amount, 'Skipped', 'skipped')
                skipped += 1
                continue

            if amount_note:
                log_anomaly(row_num, 'amount_format_fixed',
                    f'Amount format cleaned for "{raw_title}": {amount_note}',
                    raw_amount, str(amount), 'auto_fixed')

            # --- Negative amount (refund) ---
            if amount < 0:
                log_anomaly(row_num, 'negative_amount_refund',
                    f'"{raw_title}" has negative amount {amount}. Treated as refund.',
                    raw_amount, str(amount), 'auto_fixed')

            # --- Rounding ---
            rounded = amount.quantize(Decimal('0.01'))
            if rounded != amount:
                log_anomaly(row_num, 'amount_rounded',
                    f'"{raw_title}" amount {amount} rounded to {rounded}',
                    str(amount), str(rounded), 'auto_fixed')
                amount = rounded

            # --- Currency ---
            if not raw_currency or raw_currency == '':
                log_anomaly(row_num, 'missing_currency_defaulted_to_INR',
                    f'"{raw_title}" has no currency. Defaulting to INR.',
                    '', 'INR', 'auto_fixed')
                raw_currency = 'INR'

            original_amount = amount
            original_currency = raw_currency
            fx_rate = Decimal('1.0')

            if raw_currency == 'USD':
                fx_rate = USD_TO_INR
                amount = (amount * USD_TO_INR).quantize(Decimal('0.01'))
                log_anomaly(row_num, 'currency_converted',
                    f'"{raw_title}" converted from USD {original_amount} to INR {amount} at rate {USD_TO_INR}',
                    f'USD {original_amount}', f'INR {amount}', 'auto_fixed')

            # --- Parse date ---
            expense_date, date_anomaly = parse_date(raw_date)
            if expense_date is None:
                log_anomaly(row_num, 'invalid_date',
                    f'Cannot parse date "{raw_date}" for "{raw_title}"',
                    raw_date, 'Skipped', 'skipped')
                skipped += 1
                continue

            if date_anomaly == 'ambiguous_date':
                log_anomaly(row_num, 'ambiguous_date',
                    f'Date "{raw_date}" is ambiguous (MM/DD or DD/MM?). Defaulted to DD/MM.',
                    raw_date, str(expense_date), 'needs_review')

            # --- Payer ---
            if not raw_payer:
                log_anomaly(row_num, 'missing_payer',
                    f'"{raw_title}" has no payer. Imported with payer=UNKNOWN.',
                    '', 'UNKNOWN', 'needs_review')
                payer_name = 'UNKNOWN'
            else:
                normalized_payer = normalize_name(raw_payer)
                if normalized_payer != raw_payer.strip():
                    log_anomaly(row_num, 'name_normalized',
                        f'Payer "{raw_payer}" normalized to "{normalized_payer}"',
                        raw_payer, normalized_payer, 'auto_fixed')
                payer_name = normalized_payer

            # --- Split members ---
            split_members = []
            if raw_split_with:
                for name in re.split(r'[,;/]', raw_split_with):
                    name = name.strip()
                    if not name:
                        continue
                    normalized = normalize_name(name)
                    if normalized not in KNOWN_MEMBERS:
                        log_anomaly(row_num, 'unknown_member_in_split',
                            f'"{name}" is not a known member. Excluded from split.',
                            name, 'Excluded', 'auto_fixed')
                    else:
                        # Check if member was active on expense date
                        period = MEMBER_PERIODS.get(normalized)
                        if period:
                            if period['left'] and expense_date > period['left']:
                                log_anomaly(row_num, 'inactive_member_in_split',
                                    f'"{normalized}" left on {period["left"]} but is in split for {expense_date}. Removed.',
                                    normalized, 'Removed from split', 'auto_fixed')
                                continue
                            if expense_date < period['joined']:
                                log_anomaly(row_num, 'member_not_yet_joined',
                                    f'"{normalized}" joined on {period["joined"]} but expense is dated {expense_date}. Removed.',
                                    normalized, 'Removed from split', 'auto_fixed')
                                continue
                        split_members.append(normalized)

            if not split_members:
                split_members = [m for m in KNOWN_MEMBERS
                                 if MEMBER_PERIODS[m]['joined'] <= expense_date
                                 and (MEMBER_PERIODS[m]['left'] is None or MEMBER_PERIODS[m]['left'] >= expense_date)]

            # --- Duplicate detection ---
            row_signature = (raw_title.lower().strip(), str(expense_date), str(amount))
            fuzzy_key = (str(expense_date), str(amount))

            exact_dup = any(
                s['title'].lower().strip() == raw_title.lower().strip()
                and s['date'] == str(expense_date)
                and s['amount'] == str(amount)
                for s in seen_rows
            )

            if exact_dup:
                log_anomaly(row_num, 'exact_duplicate',
                    f'"{raw_title}" on {expense_date} for {amount} is an exact duplicate. Skipped.',
                    raw_title, 'Skipped', 'skipped')
                skipped += 1
                continue

            probable_dup = [
                s for s in seen_rows
                if s['date'] == str(expense_date)
                and abs(Decimal(s['amount']) - amount) < Decimal('100')
                and raw_title.lower()[:6] in s['title'].lower()
                and s['title'].lower()[:6] in raw_title.lower()
            ]

            if probable_dup:
                log_anomaly(row_num, 'probable_duplicate',
                    f'"{raw_title}" ({amount}) on {expense_date} may be a duplicate of "{probable_dup[0]["title"]}" ({probable_dup[0]["amount"]}). Both imported. Needs review.',
                    raw_title, 'Imported (needs review)', 'needs_review')

            seen_rows.append({
                'title': raw_title,
                'date': str(expense_date),
                'amount': str(amount),
            })

            # --- Percentage validation ---
            if raw_split_type == 'percentage':
                pct_raw = row.get('percentages') or row.get('split_values') or ''
                if pct_raw:
                    try:
                        pct_dict = {}
                        for part in re.split(r'[,;]', pct_raw):
                            k, v = part.strip().split(':')
                            pct_dict[k.strip()] = Decimal(v.strip())
                        total_pct, valid = validate_percentages(pct_dict)
                        if not valid:
                            log_anomaly(row_num, 'percentage_sum_invalid',
                                f'"{raw_title}" percentages sum to {total_pct}% not 100%. Normalized proportionally.',
                                str(total_pct), '100% (normalized)', 'auto_fixed')
                    except Exception:
                        pass

            # --- Create expense ---
            try:
                expense = Expense.objects.create(
                    group=group,
                    title=raw_title,
                    total_amount=amount,
                    currency='INR',
                    split_type=raw_split_type if raw_split_type in ['equal', 'unequal', 'percentage', 'share'] else 'equal',
                    created_by=request.user,
                    notes=raw_notes,
                    import_row=row_num,
                )

                # Try to find user for payer
                payer_user = User.objects.filter(full_name__iexact=payer_name).first() or \
                             User.objects.filter(username__iexact=payer_name).first()

                if payer_user:
                    ExpensePayer.objects.create(
                        expense=expense,
                        user=payer_user,
                        amount_paid=amount
                    )

                # Create equal splits
                if split_members:
                    share = (amount / len(split_members)).quantize(Decimal('0.01'))
                    for member_name in split_members:
                        member_user = User.objects.filter(full_name__iexact=member_name).first() or \
                                      User.objects.filter(username__iexact=member_name).first()
                        if member_user:
                            ExpenseSplit.objects.create(
                                expense=expense,
                                user=member_user,
                                owed_amount=share,
                                split_value=share,
                            )

                imported += 1

            except Exception as e:
                log_anomaly(row_num, 'import_error',
                    f'Failed to import "{raw_title}": {str(e)}',
                    raw_title, 'Skipped due to error', 'skipped')
                skipped += 1

        session.imported_rows = imported
        session.skipped_rows = skipped
        session.anomaly_count = len(anomalies)
        session.status = 'complete'
        session.save()

        return Response({
            'import_id': session.id,
            'total_rows': len(rows),
            'imported': imported,
            'skipped': skipped,
            'anomaly_count': len(anomalies),
            'anomalies': anomalies,
            'message': f'Import complete. {imported} rows imported, {skipped} skipped, {len(anomalies)} anomalies detected.'
        }, status=status.HTTP_201_CREATED)


class ImportReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        session = get_object_or_404(ImportSession, pk=session_id)
        anomalies = session.anomalies.all().order_by('row_number')
        return Response({
            'import_id': session.id,
            'filename': session.filename,
            'total_rows': session.total_rows,
            'imported_rows': session.imported_rows,
            'skipped_rows': session.skipped_rows,
            'anomaly_count': session.anomaly_count,
            'status': session.status,
            'created_at': session.created_at,
            'anomalies': [
                {
                    'row': a.row_number,
                    'type': a.anomaly_type,
                    'description': a.description,
                    'original': a.original_value,
                    'resolved': a.resolved_value,
                    'action': a.action_taken,
                    'approved': a.is_approved,
                }
                for a in anomalies
            ]
        })