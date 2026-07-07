# Массовое удаление писем с почтового сервера Beget.

- Список почтовых ящиков - `python mails_list.py --domains domain.ru`
- Список папок - `python list_folders.py`
- Показать количество писем старше - `python clean_old.py --accounts accounts.json --days X --dry-run`
- Удалить письма старше X дней в папке INBOX - `python clean_old.py --accounts accounts.json --days X --folders INBOX`
