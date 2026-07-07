#!/usr/bin/env python3
"""Сброс паролей почтовых ящиков Beget через API."""

import argparse
import json
import os
import secrets
import string
import sys
from getpass import getpass
from pathlib import Path
from typing import Any

import requests


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
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
        errors = data.get("errors", [])
        if errors:
            first_error = errors[0]
            msg = f"{first_error.get('error_code')}: {first_error.get('error_text')}"
        else:
            msg = data.get("error_text") or str(data)
        raise RuntimeError(msg)

    answer = data.get("answer")
    if isinstance(answer, dict) and "result" in answer:
        return answer["result"]
    return answer if answer is not None else data


def generate_password(length: int = 18) -> str:
    """Генерирует надёжный пароль."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def reset_passwords(input_file: Path, dry_run: bool = False) -> None:
    login = os.getenv("BEGET_LOGIN")
    password = os.getenv("BEGET_PASSWD")

    if not login or not password:
        login = input("Beget login: ").strip()
        password = getpass("Beget password: ")

    emails: list[str] = json.loads(input_file.read_text(encoding="utf-8"))
    if not emails:
        print("❌ Файл пустой.")
        return

    # Берём домен из первого email (все должны быть с одного домена).
    domain = emails[0].split("@")[1]
    new_credentials: list[dict[str, str]] = []

    print(f"📋 Домен: {domain} | Dry-run: {dry_run}\n")

    for email in emails:
        local_part = email.split("@")[0]
        new_pass = generate_password()

        print(f"📋 {email}")

        if not dry_run:
            try:
                input_data = {
                    "domain": domain,
                    "mailbox": local_part,
                    "mailbox_password": new_pass,
                }
                result = call_beget_api("mail", "changeMailboxPassword", login, password, input_data)
                if result == True:
                    print("✅ Пароль успешно изменён")
                else:
                    print(f"❌ ОШИБКА: {result}")
            except Exception as exc:
                print(f"❌ ОШИБКА: {exc}")
                continue

        new_credentials.append({"email": email, "password": new_pass})

    # Сохраняем результат.
    results_dir = Path("results")
    results_dir.mkdir(parents=True, exist_ok=True)
    output_path = results_dir / f"new_pass_{domain}.json"

    output_path.write_text(
        json.dumps(new_credentials, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n\nГотово. Сохранено: {output_path} ({len(new_credentials)} записей)")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Сброс паролей ящиков Beget")
    parser.add_argument("--file", required=True, help="Путь к JSON-файлу со списком почт.")
    parser.add_argument("--dry-run", action="store_true", help="Только сгенерировать пароли, не менять")
    args = parser.parse_args()

    input_path = Path(args.file)
    if not input_path.exists():
        print(f"❌ Файл не найден: {input_path}")
        sys.exit(1)

    reset_passwords(input_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()