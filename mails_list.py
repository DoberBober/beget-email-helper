#!/usr/bin/env python3
"""Получение списка всех почтовых ящиков на аккаунте Beget через API."""

import argparse
import json
import os
import sys
from getpass import getpass
from pathlib import Path
from typing import Any

import requests


def load_dotenv(path: Path = Path(".env")) -> None:
    """Простая загрузка переменных из .env файла (без зависимостей)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def call_beget_api(
    section: str,
    method: str,
    login: str,
    password: str,
    input_data: dict[str, Any] | None = None,
) -> Any:
    url = f"https://api.beget.com/api/{section}/{method}"
    params: dict[str, str] = {
        "login": login,
        "passwd": password,
        "input_format": "json",
        "output_format": "json",
    }
    if input_data:
        params["input_data"] = json.dumps(input_data, ensure_ascii=False)

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()

    if data.get("status") == "error":
        raise RuntimeError(data.get("error_text") or data.get("error") or "Unknown Beget API error")

    answer = data.get("answer")

    # Некоторые методы возвращают {"answer": {"result": [...]}}.
    if isinstance(answer, dict) and "result" in answer:
        return answer["result"]

    # Большинство методов возвращают {"answer": [...] } или просто [...].
    if answer is not None:
        return answer

    return data


def get_domains(login: str, password: str) -> list[str]:
    try:
        result = call_beget_api("domain", "getList", login, password)
        domains: list[str] = []
        for item in result or []:
            if isinstance(item, dict):
                dom = item.get("fqdn") or item.get("name") or item.get("domain")
                if dom:
                    domains.append(dom)
        return domains
    except Exception as exc:
        print(f"❌ Не удалось получить список доменов: {exc}", file=sys.stderr)
        return []


def get_mailboxes(login: str, password: str, domain: str) -> list[str]:
    result = call_beget_api(
        "mail", "getMailboxList", login, password, {"domain": domain}
    )
    emails: list[str] = []
    for item in result or []:
        if isinstance(item, dict):
            mailbox = item.get("mailbox")
            if mailbox:
                emails.append(f"{mailbox}@{domain}")
    return emails


def main() -> None:
    load_dotenv()  # загружаем .env, если есть

    parser = argparse.ArgumentParser(
        description="Получить список всех почтовых ящиков Beget"
    )
    parser.add_argument("--login", default=os.getenv("BEGET_LOGIN"), help="Логин от аккаунта")
    parser.add_argument("--password", default=os.getenv("BEGET_PASSWD"), help="Пароль от API аккаунта")
    parser.add_argument("--domains", help="Домены через запятую")
    parser.add_argument(
        "--format", choices=["emails", "json"], default="emails"
    )
    args = parser.parse_args()

    login = args.login or input("Beget login: ").strip()
    password = args.password or getpass("Beget password: ")

    if args.domains:
        domains = [d.strip() for d in args.domains.split(",") if d.strip()]
    else:
        print("⏳ Получаю список доменов аккаунта...", file=sys.stderr)
        domains = get_domains(login, password)
        if not domains:
            print("Укажите домены явно через --domains", file=sys.stderr)
            sys.exit(1)

    all_emails: list[str] = []
    for domain in domains:
        print(f"🌐 {domain}", file=sys.stderr)
        try:
            emails = get_mailboxes(login, password, domain)
            all_emails.extend(emails)
            # Сохраняем в results/<domain>.json.
            saved_path = save_domain_emails(domain, emails)
            print(f"✅ Сохранено: {saved_path} ({len(emails)} ящиков)", file=sys.stderr)
            if args.format == "emails":
                for email in emails:
                    print(email)
        except Exception as exc:
            print(f"❌ Ошибка: {exc}", file=sys.stderr)

    if args.format == "json":
        print(json.dumps(sorted(all_emails), ensure_ascii=False, indent=2))


def save_domain_emails(domain: str, emails: list[str]) -> Path:
    results_dir = Path("results/mails_list")
    results_dir.mkdir(parents=True, exist_ok=True)

    file_path = results_dir / f"{domain}.json"
    file_path.write_text(
        json.dumps(sorted(emails), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return file_path

if __name__ == "__main__":
    main()