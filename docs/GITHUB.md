# Размещение проекта на GitHub

Для этого проекта рекомендуется **приватный** репозиторий. Файл `.env`, ключ OpenAI, рабочая база SQLite и журналы уже исключены через `.gitignore`.

## 1. Проверить содержимое перед публикацией

Из корня проекта:

```powershell
git status --short
git diff --check
git grep -n -I -E "OPENAI_API_KEY=sk-|BEGIN (OPENSSH|RSA) PRIVATE KEY|password[=:].+" -- . ":(exclude)docs/GITHUB.md"
```

Последняя команда не должна находить пароли или ключи. IP сервера сам по себе не является секретом, но в исходниках он не требуется.

Убедиться, что секреты игнорируются:

```powershell
git check-ignore -v .env data/assistant.sqlite3
```

## 2. Создать первый коммит

```powershell
git add .
git status --short
git commit -m "Initial Lukomorie RAG assistant"
git branch -M main
```

Перед `git commit` еще раз просмотреть список файлов. `.env` и `data/assistant.sqlite3` не должны присутствовать.

## 3. Создать приватный репозиторий на GitHub

На github.com:

1. Нажать **New repository**.
2. Назвать, например, `lukomorie-assistant`.
3. Выбрать **Private**.
4. Не добавлять README, `.gitignore` и лицензию — они уже есть локально.
5. Создать репозиторий.

## 4. Подключить remote и отправить код

Подставить владельца репозитория:

```powershell
git remote add origin https://github.com/OWNER/lukomorie-assistant.git
git push -u origin main
```

GitHub больше не принимает пароль учетной записи для Git по HTTPS. Используйте вход через Git Credential Manager или персональный токен с минимально необходимым доступом к этому репозиторию.

Вариант через GitHub CLI:

```powershell
gh auth login
gh repo create lukomorie-assistant --private --source . --remote origin --push
```

## 5. Обновлять сервер из GitHub

На сервере сначала настроить отдельный deploy key только для чтения. Затем код можно получать в новый временный каталог и синхронизировать после проверки. Не хранить `.env` в репозитории и не заменять серверный `/etc/lukomorie-assistant.env`.

Следующие команды применимы, если `/opt/lukomorie-assistant` изначально был получен через `git clone`. Текущий тестовый сервер развернут из проверенного архива, поэтому сначала нужно отдельно перевести его на Git-развертывание после создания приватного репозитория и deploy key.

Для последующих обновлений без изменения инфраструктуры:

```bash
cd /opt/lukomorie-assistant
git pull --ff-only
sudo -u lukomorie-ai /opt/lukomorie-assistant/.venv/bin/python -m app.ingest --rebuild
systemctl restart lukomorie-assistant
systemctl status lukomorie-assistant --no-pager
```

Использовать `--ff-only` безопаснее, чем принудительный reset: команда остановится, если на сервере появились расходящиеся изменения.

## Никогда не публиковать

- `.env` и ключ OpenAI;
- SSH-пароли и приватные SSH-ключи;
- `data/assistant.sqlite3`;
- серверные журналы;
- резервные копии конфигураций с секретами.

Если секрет случайно попал в коммит, одного удаления файла недостаточно: секрет нужно немедленно отозвать/сменить, а затем очистить историю репозитория.
