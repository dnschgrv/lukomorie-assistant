# Развертывание на Windows Server 2022

Целевая схема:

- публичный IP: `85.192.173.116`;
- имя: `bot.aolukomorie56.ru`;
- Apache принимает HTTP/HTTPS;
- приложение слушает только `127.0.0.1:8080`;
- каталог приложения: `C:\LukomorieAssistant`;
- каталог Apache: `C:\Apache24`.

Все команды PowerShell в инструкции, кроме проверок с рабочей станции, выполняются на сервере в окне **PowerShell от имени администратора**.

## 1. Настроить DNS

В панели управления DNS зоны `aolukomorie56.ru` создать запись:

| Тип | Имя | Значение | TTL |
|---|---|---|---|
| A | bot | 85.192.173.116 | 300 или значение по умолчанию |

Не создавать запись AAAA, если на сервере не настроен и не открыт IPv6.

Проверить с рабочего компьютера:

```powershell
Resolve-DnsName bot.aolukomorie56.ru -Type A
```

В ответе должен быть `85.192.173.116`. Получать сертификат до распространения DNS-записи не следует.

## 2. Проверить сетевой доступ

У выделенного IP должен быть прямой входящий NAT или маршрутизация на Windows Server. Если перед сервером есть роутер или облачный firewall, направить TCP 80 и 443 на сервер.

Открыть порты в Windows Firewall:

```powershell
New-NetFirewallRule -DisplayName "Lukomorie Bot HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow -Profile Any
New-NetFirewallRule -DisplayName "Lukomorie Bot HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow -Profile Any
```

Порт 8080 не открывать. Приложение привязано к `127.0.0.1`.

Проверить, что порты не заняты другим сервером:

```powershell
Get-NetTCPConnection -State Listen | Where-Object LocalPort -In 80,443,8080
```

## 3. Установить Python

Установить 64-разрядный Python 3.12 с python.org. Во время установки включить Python Launcher (`py`) и PATH.

Проверить:

```powershell
py -3.12 --version
```

## 4. Установить Apache 2.4

Apache Software Foundation публикует исходный код и перечисляет сторонних поставщиков Windows-сборок. Установить актуальную 64-разрядную сборку Apache 2.4 и Microsoft Visual C++ Redistributable, требуемый выбранной сборкой. В этой инструкции ожидается каталог `C:\Apache24`.

В `C:\Apache24\conf\httpd.conf` убедиться, что включены строки без `#`:

```apache
Listen 80
LoadModule headers_module modules/mod_headers.so
LoadModule proxy_module modules/mod_proxy.so
LoadModule proxy_http_module modules/mod_proxy_http.so
LoadModule rewrite_module modules/mod_rewrite.so
LoadModule ssl_module modules/mod_ssl.so
LoadModule socache_shmcb_module modules/mod_socache_shmcb.so
```

В конец `httpd.conf` добавить:

```apache
Include conf/extra/lukomorie-bot.conf
```

Создать службу и проверить конфигурацию:

```powershell
& "C:\Apache24\bin\httpd.exe" -t
& "C:\Apache24\bin\httpd.exe" -k install -n "Apache2.4"
Set-Service -Name "Apache2.4" -StartupType Automatic
Start-Service -Name "Apache2.4"
```

Если служба уже существует, команду `-k install` пропустить.

## 5. Скопировать приложение

Скопировать содержимое проекта в `C:\LukomorieAssistant`. В результате должны существовать:

```text
C:\LukomorieAssistant\app\server.py
C:\LukomorieAssistant\data\knowledge.json
C:\LukomorieAssistant\static\widget.js
C:\LukomorieAssistant\deploy\windows\
```

Создать окружение и рабочие каталоги:

```powershell
Set-Location C:\LukomorieAssistant
py -3.12 -m venv .venv
New-Item -ItemType Directory -Force C:\LukomorieAssistant\acme-webroot\.well-known\acme-challenge | Out-Null
New-Item -ItemType Directory -Force C:\Apache24\conf\certs | Out-Null
```

У проекта нет сторонних Python-зависимостей, поэтому `pip install` не требуется.

## 6. Создать `.env`

Скопировать `.env.example` в `.env`:

```powershell
Copy-Item C:\LukomorieAssistant\.env.example C:\LukomorieAssistant\.env
notepad C:\LukomorieAssistant\.env
```

Содержимое:

```dotenv
OPENAI_API_KEY=ВСТАВИТЬ_КЛЮЧ_OPENAI
OPENAI_CHAT_MODEL=gpt-5-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
PUBLIC_BASE_URL=https://bot.aolukomorie56.ru
ALLOWED_ORIGINS=https://aolukomorie56.ru,https://www.aolukomorie56.ru,https://bot.aolukomorie56.ru
CACHE_TTL_SECONDS=86400
TOP_K=7
MIN_RELEVANCE=0.18
RATE_LIMIT_PER_MINUTE=20
PORT=8080
HOST=127.0.0.1
```

Не добавлять кавычки вокруг значений. Ключ OpenAI нельзя вставлять в WordPress, JavaScript или Apache-конфигурацию.

Ограничить чтение файла администраторами и SYSTEM:

```powershell
icacls C:\LukomorieAssistant\.env /inheritance:r
icacls C:\LukomorieAssistant\.env /grant:r "Administrators:F" "SYSTEM:F"
```

## 7. Построить RAG-индекс

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\LukomorieAssistant\deploy\windows\build-index.ps1
```

Ожидаемый результат: `Knowledge index is ready.` В каталоге `data` появится `assistant.sqlite3`.

## 8. Запустить приложение автоматически

Установить задачу автозапуска от SYSTEM:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\LukomorieAssistant\deploy\windows\install-scheduled-task.ps1
```

Проверить локально:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/health
Get-ScheduledTask -TaskName "Lukomorie AI Assistant"
Get-Content C:\LukomorieAssistant\logs\service.log -Tail 30
```

`ok` должен быть `True`, `openai_configured` — `True`.

## 9. Настроить HTTP для проверки домена

Скопировать начальную конфигурацию:

```powershell
Copy-Item C:\LukomorieAssistant\deploy\windows\apache-http.conf C:\Apache24\conf\extra\lukomorie-bot.conf -Force
& "C:\Apache24\bin\httpd.exe" -t
Restart-Service Apache2.4
```

Создать тестовый файл:

```powershell
Set-Content -LiteralPath C:\LukomorieAssistant\acme-webroot\.well-known\acme-challenge\check.txt -Value "ok" -Encoding ASCII
Invoke-WebRequest http://bot.aolukomorie56.ru/.well-known/acme-challenge/check.txt -UseBasicParsing
```

Ответ должен содержать `ok`. Если извне нет ответа, сначала исправить DNS, NAT или firewall.

## 10. Получить TLS-сертификат

Скачать актуальную версию win-acme с `win-acme.com`, распаковать, например, в `C:\win-acme` и запустить от администратора. Для полностью автоматической настройки нужны адрес электронной почты и согласие с условиями Let's Encrypt:

```powershell
& C:\win-acme\wacs.exe `
  --source manual `
  --host bot.aolukomorie56.ru `
  --validation filesystem `
  --webroot C:\LukomorieAssistant\acme-webroot `
  --store pemfiles `
  --pemfilespath C:\Apache24\conf\certs `
  --pemfilesname bot.aolukomorie56.ru `
  --installation script `
  --script C:\LukomorieAssistant\deploy\windows\restart-apache.cmd `
  --emailaddress АДРЕС_ДЛЯ_УВЕДОМЛЕНИЙ `
  --accepttos
```

После выпуска должны появиться:

```text
C:\Apache24\conf\certs\bot.aolukomorie56.ru-chain.pem
C:\Apache24\conf\certs\bot.aolukomorie56.ru-key.pem
```

win-acme создает задачу автоматического продления. Указанный installation script проверяет конфигурацию и перезапускает Apache после обновления сертификата.

## 11. Включить HTTPS и reverse proxy

```powershell
Copy-Item C:\LukomorieAssistant\deploy\windows\apache-https.conf C:\Apache24\conf\extra\lukomorie-bot.conf -Force
& "C:\Apache24\bin\httpd.exe" -t
Restart-Service Apache2.4
```

Проверить:

```powershell
Invoke-RestMethod https://bot.aolukomorie56.ru/health
```

Затем открыть в браузере:

```text
https://bot.aolukomorie56.ru/demo
```

## 12. Подключить виджет к сайту

Добавить перед `</body>` сайта `aolukomorie56.ru`:

```html
<script
  src="https://bot.aolukomorie56.ru/widget.js"
  data-api="https://bot.aolukomorie56.ru/api/chat"
  defer></script>
```

Сначала проверить на тестовой странице или в staging-копии WordPress, затем очистить кеш сайта/CDN.

## 13. Финальная проверка

Проверить вопросы:

1. `Сколько стоит соляная камера?`
2. `Что такое ударно-волновая терапия и какие есть противопоказания?`
3. `Работает ли сауна?`
4. `Есть ли вертолетная площадка?`

Ожидается, что бот назовет цену соляной камеры, даст осторожную справку по УВТ, сообщит о пометке недоступности сауны и откажется придумывать ответ про площадку, указав телефоны администратора.

## Обслуживание

Перезапуск приложения:

```powershell
Stop-ScheduledTask -TaskName "Lukomorie AI Assistant"
Start-ScheduledTask -TaskName "Lukomorie AI Assistant"
```

Проверка Apache:

```powershell
& "C:\Apache24\bin\httpd.exe" -t
Get-Service Apache2.4
Get-Content C:\Apache24\logs\error.log -Tail 50
```

После изменения `data\knowledge.json`:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\LukomorieAssistant\deploy\windows\build-index.ps1
Stop-ScheduledTask -TaskName "Lukomorie AI Assistant"
Start-ScheduledTask -TaskName "Lukomorie AI Assistant"
```
