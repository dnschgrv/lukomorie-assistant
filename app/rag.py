import hashlib
import json
import math
import re
import sqlite3
import time
from dataclasses import dataclass
from . import config
from .openai_client import embed

TOKEN_RE = re.compile(r"[а-яёa-z0-9]+", re.I)
STOPWORDS = {"а", "без", "бы", "в", "вам", "вас", "ваш", "где", "для", "до", "есть", "и", "из", "или", "как", "какая", "какие", "какой", "ли", "мне", "можно", "на", "не", "о", "об", "от", "по", "под", "при", "про", "с", "со", "сколько", "стоит", "у", "что", "это", "я"}

# Words visitors commonly use instead of the formal names found in the price list.
QUERY_ALIASES = {
    "отдых": {"путевка", "проживание"},
    "отдохнуть": {"путевка", "проживание"},
    "отдыхать": {"путевка", "проживание"},
    "жить": {"проживание", "путевка"},
    "номер": {"проживание", "путевка"},
    "питание": {"путевка"},
    "лечением": {"лечение", "путевка"},
    "лечиться": {"лечение", "путевка"},
    "путевку": {"путевка"},
    "путевке": {"путевка"},
    "путевки": {"путевка"},
    "путёвку": {"путевка"},
    "путёвке": {"путевка"},
    "путёвки": {"путевка"},
    "массажей": {"массаж"},
    "массажа": {"массаж"},
    "масаж": {"массаж"},
    "масажа": {"массаж"},
    "процедур": {"процедура"},
    "процедуры": {"процедура"},
    "процедуре": {"процедура"},
}


def normalize(text: str) -> str:
    return " ".join(TOKEN_RE.findall(text.lower().replace("ё", "е")))


def tokens(text: str) -> set[str]:
    result = {t for t in normalize(text).split() if len(t) > 1 and t not in STOPWORDS}
    for token in tuple(result):
        result.update(QUERY_ALIASES.get(token, ()))
    return result


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    den = math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))
    return dot / den if den else 0.0


@dataclass
class Hit:
    score: float
    content: str
    source: str
    title: str


class KnowledgeBase:
    def __init__(self):
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY, title TEXT, content TEXT, source TEXT, embedding TEXT);
          CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY, answer TEXT, created REAL);
        """)
        self.db.commit()
        self.ensure_loaded()

    def _chunks_from_json(self) -> list[dict]:
        data = json.loads(config.KB_PATH.read_text(encoding="utf-8"))
        chunks = []
        for item in data["site_facts"]:
            chunks.append({"title": item["title"], "content": item["text"], "source": item["source"]})
        for item in data["packages"]:
            content = f"{item['name']}. Цена: {item['price_rub']} руб. {item['unit']}. Действует с {item['valid_from']}. {item.get('details','')}"
            chunks.append({"title": item["name"], "content": content, "source": item["source"]})
        guides = data["procedure_guides"]
        for item in data["medical_services"]:
            status = {"available": "доступность не ограничена пометкой прайса", "unavailable": "по пометке прайса услуга недоступна", "limited": "в прайсе есть ограничивающая пометка; доступность нужно уточнить"}[item["status"]]
            content = f"{item['name']}. Цена {item['price_rub']} руб. за одну услугу/процедуру. Продолжительность: {item.get('duration','не указана')}. Прейскурант действует с 01.06.2025. Статус: {status}."
            if item.get("note"):
                content += f" Пометка исходного прайса: {item['note']}."
            guide = guides.get(item.get("guide", ""))
            sources = [item["source"]]
            if guide:
                content += f" Что это: {guide['description']} Возможные показания: {guide['indications']} Основные противопоказания и ограничения: {guide['contraindications']} Процедуру назначает врач после оценки состояния пациента."
                sources.append(guide["source"])
            chunks.append({"title": item["name"], "content": content, "source": " | ".join(sources)})
        return chunks

    def price_answer(self, query: str) -> str | None:
        """Answer straightforward price questions directly from the price list."""
        normalized = normalize(query)
        if not any(word in normalized.split() for word in ("сколько", "цена", "стоимость", "почем")):
            return None
        data = json.loads(config.KB_PATH.read_text(encoding="utf-8"))
        services = data["medical_services"]
        qtokens = tokens(query)
        if "массаж" in qtokens:
            massage_services = [item for item in services if "массаж" in normalize(item["name"]) and item["status"] == "available"]
            qualifiers = qtokens - {"массаж", "массажа", "масаж", "масажа", "цена", "стоимость", "почем", "услуга", "процедура", "руб", "рублей"}
            ranked = []
            for item in massage_services:
                title_tokens = tokens(item["name"])
                score = len(qualifiers & title_tokens) / max(1, len(qualifiers))
                if normalize(item["name"]) in normalized:
                    score += 1
                ranked.append((score, item))
            ranked.sort(key=lambda pair: (pair[0], -len(pair[1]["name"])), reverse=True)
            if qualifiers and ranked and ranked[0][0] >= 0.5:
                item = ranked[0][1]
                price_text = f"{item['price_rub']:,}".replace(",", " ")
                return (f"{item['name']} стоит {price_text} ₽, продолжительность — {item.get('duration', 'не указана')}. "
                        "Цена указана за одну процедуру по прейскуранту с 01.06.2025.")
            prices = [item["price_rub"] for item in massage_services]
            examples = ["массаж головы — 350 ₽", "воротниковой зоны — 500 ₽", "спины — 700 ₽", "лица — 500 ₽", "стопы и голени — 400 ₽"]
            return (f"В прейскуранте есть {len(massage_services)} видов массажа стоимостью от {min(prices)} до {max(prices)} ₽ за процедуру. "
                    f"Например: {', '.join(examples)}. Уточните, пожалуйста, какую зону или вид массажа вы имеете в виду — назову точную цену и длительность. "
                    "Прейскурант действует с 01.06.2025.")
        return None

    def ensure_loaded(self, rebuild: bool = False):
        wanted = self._chunks_from_json()
        digest = hashlib.sha256(config.KB_PATH.read_bytes()).hexdigest()
        current = self.db.execute("SELECT content FROM chunks WHERE id='__version__'").fetchone()
        if not rebuild and current and current[0] == digest:
            return
        self.db.execute("DELETE FROM chunks")
        for i, chunk in enumerate(wanted):
            cid = hashlib.sha256((chunk["title"] + chunk["content"]).encode()).hexdigest()
            self.db.execute("INSERT INTO chunks VALUES(?,?,?,?,NULL)", (cid, chunk["title"], chunk["content"], chunk["source"]))
        self.db.execute("INSERT INTO chunks VALUES('__version__','version',?,'',NULL)", (digest,))
        self.db.commit()

    def build_embeddings(self):
        if not config.OPENAI_API_KEY:
            return
        rows = self.db.execute("SELECT id, content FROM chunks WHERE id != '__version__' AND embedding IS NULL").fetchall()
        for start in range(0, len(rows), 64):
            batch = rows[start:start + 64]
            vectors = embed([r[1] for r in batch])
            for (cid, _), vector in zip(batch, vectors):
                self.db.execute("UPDATE chunks SET embedding=? WHERE id=?", (json.dumps(vector), cid))
            self.db.commit()

    def search(self, query: str, limit: int | None = None) -> list[Hit]:
        limit = limit or config.TOP_K
        rows = self.db.execute("SELECT title, content, source, embedding FROM chunks WHERE id != '__version__'").fetchall()
        qtokens = tokens(query)
        qvec = None
        if config.OPENAI_API_KEY and any(r[3] for r in rows):
            try:
                qvec = embed([query])[0]
            except Exception:
                qvec = None
        scored = []
        normalized_query = normalize(query)
        for title, content, source, raw_vec in rows:
            hay = tokens(title + " " + content)
            overlap = len(qtokens & hay) / max(1, len(qtokens))
            phrase = 0.45 if normalized_query and normalized_query in normalize(title + " " + content) else 0.0
            semantic = cosine(qvec, json.loads(raw_vec)) if qvec and raw_vec else 0.0
            score = max(overlap + phrase, semantic)
            scored.append(Hit(score, content, source, title))
        return sorted(scored, key=lambda x: x.score, reverse=True)[:limit]

    def context(self, query: str) -> tuple[str, list[Hit]]:
        hits = self.search(query)
        if not hits or hits[0].score < config.MIN_RELEVANCE:
            return "", hits
        return "\n\n".join(f"[{h.title}]\n{h.content}\nИсточник: {h.source}" for h in hits), hits

    def cache_key(self, question: str) -> str:
        raw = f"v2|{config.CHAT_MODEL}|{normalize(question)}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get_cached(self, question: str) -> str | None:
        row = self.db.execute("SELECT answer, created FROM cache WHERE key=?", (self.cache_key(question),)).fetchone()
        if row and time.time() - row[1] <= config.CACHE_TTL:
            return row[0]
        return None

    def put_cached(self, question: str, answer: str):
        self.db.execute("INSERT OR REPLACE INTO cache VALUES(?,?,?)", (self.cache_key(question), answer, time.time()))
        self.db.commit()
