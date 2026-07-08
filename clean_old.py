#!/usr/bin/env python3
"""Clean old emails on Beget via IMAP. Dry-run first!"""

import argparse
import imaplib
import json
import ssl
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

IMAP_HOST = "imap.beget.com"
IMAP_PORT = 993

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def get_imap_date(days_ago: int) -> str:
    """Return date in IMAP format DD-MMM-YYYY (English months)."""
    dt = datetime.now() - timedelta(days=days_ago)
    return f"{dt.day:02d}-{MONTHS[dt.month-1]}-{dt.year}"


def clean_account(
    email: str,
    password: str,
    days: int,
    folders: List[str],
    dry_run: bool,
) -> int:
    """Return number of deleted messages for the account."""
    context = ssl.create_default_context()
    total_deleted = 0

    with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=context) as imap:
        imap.login(email, password)

        for folder in folders:
            try:
                readonly = dry_run
                status, _ = imap.select(folder, readonly=readonly)
                if status != "OK":
                    print(f"❌ [{email}] {folder}: ошибка выбора ({status})")
                    continue

                cutoff = get_imap_date(days)
                status, data = imap.uid("SEARCH", f'(BEFORE "{cutoff}")')
                if status != "OK" or not data or not data[0]:
                    print(f"❌ [{email}] {folder}: 0 старых писем")
                    continue

                uids: List[bytes] = data[0].split()
                count = len(uids)
                print(f"📋 [{email}] {folder}: {count} писем старше {cutoff}")

                if count == 0 or dry_run:
                    total_deleted += count
                    continue

                # Chunked STORE to avoid huge command limits.
                CHUNK = 500
                for i in range(0, count, CHUNK):
                    chunk = uids[i : i + CHUNK]
                    imap.uid("STORE", b",".join(chunk), "+FLAGS", r"(\Deleted)")
                imap.expunge()

                print(f"✅ [{email}] {folder}: удалено {count}")
                total_deleted += count

            except Exception as exc:
                print(f"❌ [{email}] {folder}: ERROR {exc}")

        imap.logout()
    return total_deleted


def main() -> None:
    parser = argparse.ArgumentParser(description="Удаляет старые письма на почтовике Beget через IMAP")
    parser.add_argument("--accounts", required=True, help="Путь к JSON-файлу с массивом {email, password}")
    parser.add_argument("--days", type=int, default=365, help="Удалить письма старше X дней (по умолчанию 365)")
    parser.add_argument(
        "--folders",
        default="INBOX",
        help="Список папок через запятую (по умолчанию: INBOX). Например: INBOX,INBOX.Junk",
    )
    parser.add_argument("--dry-run", action="store_true", help="Просто посчитать, без удаления")
    args = parser.parse_args()

    accounts_file = Path(args.accounts)
    if not accounts_file.exists():
        print(f"❌ Файл с почтовыми ящиками не найден {accounts_file}")
        return

    accounts: List[dict] = json.loads(accounts_file.read_text(encoding="utf-8"))
    folders = [f.strip() for f in args.folders.split(",") if f.strip()]

    print(f"📋 Хост: {IMAP_HOST} | Количество дней: {args.days} | Dry-run: {args.dry_run}")
    print(f"📋 Папки: {folders}\n")

    grand_total = 0
    for acc in accounts:
        email = acc["email"]
        password = acc["password"]
        print(f"⏳ Обрабатываю {email}...")
        deleted = clean_account(email, password, args.days, folders, args.dry_run)
        grand_total += deleted

    print(f"\n\nВсего удалено: {grand_total}" if not args.dry_run else f"\n\nВсего писем: {grand_total}")


if __name__ == "__main__":
    main()