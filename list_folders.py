#!/usr/bin/env python3
import imaplib
import ssl
import getpass

email = input("Email: ").strip()
password = getpass.getpass("Password: ")

with imaplib.IMAP4_SSL("imap.beget.com", 993, ssl_context=ssl.create_default_context()) as imap:
    imap.login(email, password)
    status, data = imap.list()
    print("\n\nДоступные папки (IMAP LIST):")
    for item in data:
        print(item.decode(errors="replace"))
    imap.logout()