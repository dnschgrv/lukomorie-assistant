import json
import mimetypes
import re
import time
from collections import defaultdict, deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import config
from .openai_client import OpenAIError, answer, web_answer
from .rag import KnowledgeBase

STATIC = config.ROOT / "static"
KB = KnowledgeBase()
REQUESTS = defaultdict(deque)

MEDICAL_HINTS = {"процедура", "процедуре", "процедуры", "терапия", "терапии", "массаж", "ванна", "ингаляция", "лечение", "показания", "противопоказания"}
GENERAL_HINTS = {"санаторий", "санатории", "лукоморье", "отдых", "путевка", "путёвка", "номер", "питание", "заезд", "бассейн", "услуга", "услуги"}


def web_fallback_kind(question: str) -> str | None:
    words = set(re.findall(r"[а-яёa-z]+", question.lower()))
    if words & MEDICAL_HINTS or any(word.endswith(("терапия", "терапии", "массаж")) for word in words):
        return "medical"
    if words & GENERAL_HINTS:
        return "official"
    return None


def local_answer_from_hits(hits) -> str:
    """Return a useful database fact when generation is temporarily unavailable."""
    if not hits:
        return config.FALLBACK
    content = hits[0].content.strip()
    content = re.sub(r"\s*Прейскурант действует с \d{2}\.\d{2}\.\d{4}\.", "", content, flags=re.I)
    content = re.sub(r"\s*Действует с \d{4}-\d{2}-\d{2}\.", "", content, flags=re.I)
    return ("Сейчас не удалось сформировать расширенный ответ, но в базе санатория указано: "
            f"{content} Если нужна дополнительная проверка, позвоните администратору: "
            "8 (35363) 4-33-56 или 8 (800) 500-28-40.")


def _person_count(text: str) -> int | None:
    lowered = text.lower().replace("ё", "е")
    match = re.search(r"\b(\d{1,2})\s*(?:человек|человека|человеку|гостя|гостей|клиента|клиентов)\b", lowered)
    if match:
        count = int(match.group(1))
        return count if 1 <= count <= 30 else None
    forms = {
        "один": 1, "одного": 1, "одна": 1,
        "двое": 2, "двоих": 2, "два": 2, "двух": 2,
        "трое": 3, "троих": 3, "три": 3, "трех": 3,
        "четверо": 4, "четверых": 4, "четыре": 4, "четырех": 4,
        "пятеро": 5, "пятерых": 5, "пять": 5,
    }
    if re.search(r"\b(?:человек|человека|гостя|гостей|клиента|клиентов|нас|на)\b", lowered):
        for word, count in forms.items():
            if re.search(rf"\b{word}\b", lowered):
                return count
    return None


def _package_days(text: str) -> int | None:
    lowered = text.lower().replace("ё", "е")
    if not _mentions_package(lowered):
        return None
    match = re.search(r"\b(\d{1,3})\s*(?:день|дня|дней|сутки|суток)\b", lowered)
    if not match:
        return None
    days = int(match.group(1))
    return days if 1 <= days <= 365 else None


def _mentions_package(text: str) -> bool:
    lowered = text.lower().replace("ё", "е")
    return bool(re.search(r"\b(?:путевк\w*|отдых\w*|лечени\w*|питани\w*)\b", lowered))


def _people_label(count: int) -> str:
    ending = "человека" if count % 10 in {2, 3, 4} and count % 100 not in {12, 13, 14} else "человек"
    return f"{count} {ending}"


def _package_total_answer(people: int, days: int | None) -> str:
    if days is None:
        total = 5100 * people
        total_text = f"{total:,}".replace(",", " ")
        return (f"Для {people} гостей путёвка стоит {total_text} ₽ за один день "
                f"({_people_label(people)} × 5 100 ₽). В расчёте — по одному месту на каждого гостя в двухместных номерах. "
                "В тариф входят проживание, трёхразовое питание и лечение по назначению врача. "
                "Скажите количество дней — посчитаю полную стоимость.")
    per_person = days * 5100
    total = per_person * people
    total_text = f"{total:,}".replace(",", " ")
    per_person_text = f"{per_person:,}".replace(",", " ")
    return (f"Для {people} гостей путёвка на {days} дней стоит {total_text} ₽ "
            f"({days} дней × {_people_label(people)} × 5 100 ₽). На одного человека — {per_person_text} ₽. "
            "В тариф входят проживание, трёхразовое питание и лечение по назначению врача.")


def _conversation_calculation(question: str, history: list[dict]) -> str | None:
    """Continue a recent deterministic package calculation without calling OpenAI."""
    people = _person_count(question)
    if people is None:
        return None
    days = _package_days(question)
    has_package_context = _mentions_package(question)
    for item in reversed(history[-6:]):
        if item.get("role") != "user":
            continue
        previous = str(item.get("content", ""))[:1000]
        has_package_context = has_package_context or _mentions_package(previous)
        if days is None:
            days = _package_days(previous)
        if has_package_context and days is not None:
            break
    if not has_package_context:
        return None
    return _package_total_answer(people, days)


def direct_answer(question: str, history: list[dict] | None = None) -> str | None:
    """Handle common messages that have safe, deterministic answers."""
    history = history or []
    continued = _conversation_calculation(question, history)
    if continued:
        return continued
    normalized = " ".join(re.findall(r"[а-яёa-z]+", question.lower()))
    words = set(normalized.split())
    greetings = {"здравствуйте", "здравствуй", "привет", "добрый", "день", "вечер", "утро"}
    if words and words <= greetings:
        return "Здравствуйте! Рад помочь. Можете спросить о стоимости путевок и процедур, лечении, размещении, питании, документах для заезда или контактах санатория «Лукоморье»."
    capability_phrases = ("что ты умеешь", "чем можешь помочь", "что вы умеете", "чем вы можете помочь")
    if any(phrase in normalized for phrase in capability_phrases):
        return ("Я могу подсказать цены на путевки и медицинские услуги, рассказать о процедурах, размещении, питании, "
                "лечебных профилях, документах для заезда и контактах «Лукоморья». Например, спросите: «Сколько будет "
                "стоить путевка на 5 дней?» или «Расскажите о соляной камере». Отвечаю только по базе санатория и не заменяю консультацию врача.")
    days_match = re.search(r"\b(\d{1,3})\s*(?:день|дня|дней|сутки|суток)\b", question.lower())
    package_words = {"отдых", "путевка", "путёвка", "проживание", "номер"}
    wants_full_package = bool(words & package_words) and bool(words & {"лечение", "лечением", "питание", "питанием", "путевка", "путёвка"})
    if wants_full_package:
        days = int(days_match.group(1)) if days_match else None
        people = _person_count(question)
        if people:
            return _package_total_answer(people, days)
        if days:
            total = 5100 * days
            total_text = f"{total:,}".replace(",", " ")
            return (f"Для одного человека в двухместном номере путёвка на {days} дней стоит {total_text} ₽ "
                    f"({days} × 5 100 ₽). В стоимость одного койко-дня входят проживание — 2 000 ₽, "
                    "трёхразовое питание — 1 500 ₽ и лечение по назначению врача — 1 600 ₽. "
                    "Если гостей несколько, скажите количество — посчитаю общую сумму.")
        return ("Путёвка для одного человека в двухместном номере стоит 5 100 ₽ за койко-день: проживание — 2 000 ₽, "
                "трёхразовое питание — 1 500 ₽ и лечение по назначению врача — 1 600 ₽.")
    if words & {"проживание", "номер", "жить"} and not words & {"лечение", "лечением", "питание", "питанием"}:
        days = int(days_match.group(1)) if days_match else None
        if days:
            total_text = f"{2000 * days:,}".replace(",", " ")
            return (f"Проживание для одного человека в двухместном номере на {days} дней — {total_text} ₽ "
                    f"({days} × 2 000 ₽). Это стоимость проживания без питания и лечения по прейскуранту с 01.01.2026.")
        return "Проживание в двухместном номере стоит 2 000 ₽ за один койко-день на человека без питания и лечения."
    if "какие процедуры" in normalized or "процедуры есть" in normalized:
        return ("В «Лукоморье» представлены физиотерапия, водо- и теплолечение, галотерапия в соляной камере, ингаляции, "
                "лечебный массаж, ЛФК, кислородотерапия и коктейли, гирудотерапия, озонотерапия и другие услуги. "
                "Доступность отдельных аппаратов различается, поэтому лучше спросите меня о конкретной процедуре — расскажу стоимость, длительность и отметку о доступности из прейскуранта.")
    if normalized in {"расскажи о санатории", "расскажите о санатории", "о санатории", "что за санаторий"}:
        return ("«Лукоморье» — санаторий-профилакторий в посёлке Энергетик Оренбургской области. Два здания соединены тёплой галереей; "
                "в двухместных комнатах указаны душ, санузел, балкон, кондиционер, телевизор и мягкая мебель. Санаторий работает ежедневно с 08:00 до 20:00. "
                "Могу подробнее рассказать о лечении, процедурах, размещении, путёвках или документах для заезда.")
    return None


def allowed(origin: str | None) -> bool:
    return not origin or origin.rstrip("/") in config.ALLOWED_ORIGINS


class Handler(BaseHTTPRequestHandler):
    server_version = "LukomorieAssistant/1.0"

    def log_message(self, fmt, *args):
        # Never log request bodies or query text.
        print(f"{self.address_string()} {self.command} {urlparse(self.path).path} {args[1] if len(args) > 1 else ''}")

    def _cors(self):
        origin = self.headers.get("Origin")
        if origin and allowed(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def json_response(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        if not allowed(self.headers.get("Origin")):
            return self.json_response(HTTPStatus.FORBIDDEN, {"error": "origin_not_allowed"})
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self.json_response(200, {"ok": True, "openai_configured": bool(config.OPENAI_API_KEY)})
        files = {"/widget.js": "widget.js", "/widget.css": "widget.css", "/demo": "demo.html", "/": "demo.html"}
        if path not in files:
            return self.send_error(404)
        file = STATIC / files[path]
        body = file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", (mimetypes.guess_type(file.name)[0] or "application/octet-stream") + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=300")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _rate_limited(self) -> bool:
        ip = self.client_address[0]
        now = time.time()
        bucket = REQUESTS[ip]
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= config.RATE_LIMIT:
            return True
        bucket.append(now)
        return False

    def do_POST(self):
        if urlparse(self.path).path != "/api/chat":
            return self.send_error(404)
        if not allowed(self.headers.get("Origin")):
            return self.json_response(403, {"error": "origin_not_allowed"})
        if self._rate_limited():
            return self.json_response(429, {"answer": "Слишком много сообщений. Пожалуйста, повторите через минуту."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 20000:
                raise ValueError
            payload = json.loads(self.rfile.read(length))
            question = str(payload.get("message", "")).strip()
            history = payload.get("history", [])
            if not question or len(question) > 1500 or not isinstance(history, list):
                raise ValueError
        except (ValueError, TypeError, json.JSONDecodeError):
            return self.json_response(400, {"error": "invalid_request", "answer": "Не удалось прочитать вопрос. Сформулируйте его короче."})

        direct = direct_answer(question, history)
        if direct:
            return self.json_response(200, {"answer": direct, "sources": []})

        price = KB.price_answer(question)
        if price:
            return self.json_response(200, {"answer": price, "sources": ["с 01.06.2025 Прейскурант на медуслуги отметка.xls"]})

        cached = KB.get_cached(question) if not history else None
        if cached:
            return self.json_response(200, {"answer": cached, "cached": True})
        context, hits = KB.context(question)
        if not context:
            kind = web_fallback_kind(question)
            if not kind:
                return self.json_response(200, {"answer": config.FALLBACK, "sources": []})
            try:
                result, sources = web_answer(question, medical=kind == "medical")
            except OpenAIError as exc:
                print(f"OpenAI web search failed: {exc}", flush=True)
                return self.json_response(200, {"answer": config.FALLBACK, "sources": []})
            if not history:
                KB.put_cached(question, result)
            return self.json_response(200, {"answer": result, "sources": sources})
        try:
            result = answer(question, context, history)
        except OpenAIError as exc:
            # The question itself is deliberately not logged.
            print(f"OpenAI request failed: {exc}", flush=True)
            return self.json_response(200, {"answer": local_answer_from_hits(hits), "sources": [hits[0].source]})
        if not history:
            KB.put_cached(question, result)
        sources = []
        for hit in hits[:3]:
            for source in hit.source.split(" | "):
                if source not in sources:
                    sources.append(source)
        return self.json_response(200, {"answer": result, "sources": sources[:4]})


def main():
    server = ThreadingHTTPServer((config.HOST, config.PORT), Handler)
    print(f"Lukomorie assistant listening on {config.HOST}:{config.PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
