import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser

class ImportCSVView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    KNOWN_MEMBERS = {'Alice', 'Bob', 'Priya', 'Sam', 'Meera', 'Kabir'}
    KNOWN_CURRENCIES = {'INR', 'USD', 'EUR'}

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded'}, status=400)

        content = file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))

        imported = []
        anomalies = []
        skipped = []
        seen = set()

        rows = list(reader)

        for i, row in enumerate(rows, start=2):  # row 1 = header
            row_anomalies = []
            action = 'imported'

            # --- 1. Parse date ---
            date_raw = row.get('date', '').strip()
            date_parsed = self._parse_date(date_raw)
            if not date_parsed:
                row_anomalies.append(f'Unrecognized date format: "{date_raw}"')
                action = 'skipped'
            elif date_raw != date_parsed.strftime('%Y-%m-%d'):
                row_anomalies.append(f'Non-standard date format "{date_raw}" normalized to "{date_parsed}"')

            # --- 2. Parse amount ---
            amount_raw = row.get('amount', '').strip()
            amount_cleaned = amount_raw.replace(',', '').strip()
            try:
                amount = Decimal(amount_cleaned)
                if amount_raw != amount_cleaned:
                    row_anomalies.append(f'Amount "{amount_raw}" had comma — cleaned to {amount}')
                if amount < 0:
                    row_anomalies.append(f'Negative amount {amount} — treated as refund, skipped')
                    action = 'skipped'
                elif amount == 0:
                    row_anomalies.append(f'Zero amount — skipped')
                    action = 'skipped'
                else:
                    amount = round(amount, 2)
                    amount_raw_dec = Decimal(amount_cleaned)
                    if amount_raw_dec != amount:
                        row_anomalies.append(f'Amount rounded from {amount_raw_dec} to {amount}')
            except InvalidOperation:
                row_anomalies.append(f'Invalid amount "{amount_raw}" — skipped')
                action = 'skipped'
                amount = None

            # --- 3. Currency ---
            currency = row.get('currency', '').strip().upper()
            if not currency:
                row_anomalies.append('Missing currency — defaulted to INR')
                currency = 'INR'
            elif currency not in self.KNOWN_CURRENCIES:
                row_anomalies.append(f'Unknown currency "{currency}" — defaulted to INR')
                currency = 'INR'
            elif currency == 'USD':
                row_anomalies.append(f'USD expense — kept as-is (no conversion)')

            # --- 4. Description ---
            description = row.get('description', '').strip()
            if not description:
                row_anomalies.append('Missing description')

            # --- 5. Paid by ---
            paid_by_raw = row.get('paid_by', '').strip()
            paid_by = paid_by_raw.title()
            if not paid_by_raw:
                row_anomalies.append('Missing paid_by — skipped')
                action = 'skipped'
            elif paid_by not in self.KNOWN_MEMBERS:
                row_anomalies.append(f'Unknown payer "{paid_by_raw}" — skipped')
                action = 'skipped'
            elif paid_by != paid_by_raw:
                row_anomalies.append(f'Payer name normalized "{paid_by_raw}" → "{paid_by}"')

            # --- 6. Split among ---
            split_raw = row.get('split_among', '').strip()
            split_members = [m.strip().title() for m in split_raw.split(',') if m.strip()]
            unknown_members = [m for m in split_members if m not in self.KNOWN_MEMBERS]
            if unknown_members:
                row_anomalies.append(f'Unknown split members {unknown_members} — removed from split')
                split_members = [m for m in split_members if m in self.KNOWN_MEMBERS]
            if not split_members:
                row_anomalies.append('No valid split members — skipped')
                action = 'skipped'

            # --- 7. Split type ---
            split_type = row.get('split_type', '').strip().lower()
            percentages_raw = row.get('percentages', '').strip()
            if split_type == 'percentage' and percentages_raw:
                try:
                    pcts = [Decimal(p.strip()) for p in percentages_raw.split(',') if p.strip()]
                    total = sum(pcts)
                    if abs(total - 100) > Decimal('0.01'):
                        row_anomalies.append(f'Percentages sum to {total}% (not 100%) — normalized')
                        pcts = [round(p / total * 100, 2) for p in pcts]
                except Exception:
                    row_anomalies.append(f'Invalid percentages "{percentages_raw}" — defaulted to equal split')
                    split_type = 'equal'

            # --- 8. Settlement detection ---
            if description and any(w in description.lower() for w in ['settlement', 'deposit', 'transfer', 'repay', 'paid back']):
                row_anomalies.append(f'Looks like a settlement/transfer, not an expense — skipped')
                action = 'skipped'

            # --- 9. Duplicate detection ---
            if date_parsed and amount and paid_by:
                key = (str(date_parsed), str(amount), paid_by, description.lower())
                if key in seen:
                    row_anomalies.append(f'Duplicate entry detected — skipped')
                    action = 'skipped'
                else:
                    seen.add(key)

            # --- Compile row result ---
            result = {
                'row': i,
                'description': description,
                'date': str(date_parsed) if date_parsed else date_raw,
                'amount': str(amount) if amount else None,
                'currency': currency,
                'paid_by': paid_by if paid_by_raw else None,
                'split_among': split_members,
                'split_type': split_type,
                'action': action,
                'anomalies': row_anomalies,
            }

            if row_anomalies:
                anomalies.append(result)

            if action == 'imported':
                imported.append(result)
            else:
                skipped.append(result)

        report = {
            'summary': {
                'total_rows': len(rows),
                'imported': len(imported),
                'skipped': len(skipped),
                'anomalies_detected': len(anomalies),
            },
            'imported': imported,
            'skipped': skipped,
            'anomaly_report': anomalies,
        }

        return Response(report, status=200)

    def _parse_date(self, date_str):
        formats = [
            '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y',
            '%d-%m-%Y', '%B %d', '%b %d',
            '%d %B %Y', '%d %b %Y',
            '%b %d, %Y', '%B %d, %Y',
        ]
        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                if parsed.year == 1900:
                    parsed = parsed.replace(year=2026)
                return parsed.date()
            except ValueError:
                continue
        return None