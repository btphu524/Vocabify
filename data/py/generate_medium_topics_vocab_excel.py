import json
import random
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None


OUTPUT_EXCEL = Path("vocab_medium_10topics_10words.xlsx")
DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{}"
LEVEL = "medium"
WORDS_PER_TOPIC = 10

TOPICS_IN_ORDER = [
    "daily activities",
    "house and furniture",
    "weather",
    "shopping",
    "transportation",
    "hobbies",
    "health",
    "emotions",
    "travel",
    "technology",
]

# Larger pools to replace words that miss required API fields.
TOPIC_WORD_POOLS = {
    "daily activities": [
        "wake", "shower", "brush", "commute", "exercise", "cook", "clean", "study", "work", "relax",
        "stretch", "plan", "practice", "review", "organize", "schedule", "laundry", "vacuum", "email", "message",
        "meditate", "journal", "nap", "prepare", "pack", "unpack", "deadline", "meeting", "break", "routine",
    ],
    "house and furniture": [
        "apartment", "balcony", "basement", "hallway", "kitchen", "bathroom", "bedroom", "living room", "garage", "garden",
        "sofa", "couch", "armchair", "table", "desk", "bookshelf", "wardrobe", "drawer", "cabinet", "mirror",
        "curtain", "carpet", "rug", "blanket", "pillow", "mattress", "lamp", "ceiling", "window", "door",
    ],
    "weather": [
        "forecast", "temperature", "humidity", "breeze", "windy", "storm", "thunder", "lightning", "drizzle", "shower",
        "rainfall", "cloudy", "overcast", "sunny", "foggy", "mist", "heatwave", "drought", "freezing", "chilly",
        "snowfall", "blizzard", "hail", "rainbow", "climate", "seasonal", "pressure", "sunrise", "sunset", "umbrella",
    ],
    "shopping": [
        "checkout", "receipt", "discount", "bargain", "refund", "exchange", "warranty", "cashier", "aisle", "basket",
        "cart", "purchase", "order", "delivery", "shipping", "customer", "store", "online", "payment", "invoice",
        "brand", "size", "fitting", "promotion", "coupon", "outlet", "queue", "return", "price tag", "membership",
    ],
    "transportation": [
        "traffic", "highway", "intersection", "lane", "pedestrian", "crosswalk", "helmet", "seatbelt", "commute", "timetable",
        "station", "platform", "subway", "tram", "ferry", "airline", "runway", "terminal", "passport", "luggage",
        "navigate", "route", "detour", "delay", "arrival", "departure", "ticket", "fare", "transfer", "parking",
    ],
    "hobbies": [
        "photography", "painting", "drawing", "gardening", "cooking", "baking", "reading", "writing", "hiking", "camping",
        "fishing", "knitting", "sewing", "collecting", "chess", "puzzle", "yoga", "cycling", "swimming", "gaming",
        "guitar", "piano", "singing", "dancing", "calligraphy", "craft", "origami", "jogging", "sketch", "blogging",
    ],
    "health": [
        "symptom", "diagnosis", "treatment", "medicine", "prescription", "infection", "allergy", "fever", "cough", "headache",
        "stomachache", "nutrition", "hydration", "vaccine", "appointment", "clinic", "hospital", "pharmacy", "recovery", "exercise",
        "stress", "sleep", "healthy", "injury", "bandage", "therapy", "checkup", "disease", "surgery", "doctor",
    ],
    "emotions": [
        "anxious", "nervous", "excited", "proud", "grateful", "lonely", "frustrated", "angry", "calm", "relieved",
        "confident", "embarrassed", "jealous", "hopeful", "sad", "happy", "worried", "surprised", "scared", "curious",
        "disappointed", "ashamed", "content", "miserable", "stressed", "optimistic", "pessimistic", "overwhelmed", "motivated", "bored",
    ],
    "travel": [
        "itinerary", "reservation", "booking", "accommodation", "hostel", "hotel", "sightseeing", "landmark", "souvenir", "passport",
        "visa", "customs", "departure", "arrival", "delay", "connection", "tour", "guide", "map", "explore",
        "adventure", "backpack", "luggage", "check-in", "check out", "destination", "trip", "journey", "airport", "ticket",
    ],
    "technology": [
        "software", "hardware", "device", "smartphone", "laptop", "tablet", "charger", "battery", "wireless", "network",
        "internet", "browser", "website", "password", "account", "download", "upload", "update", "backup", "storage",
        "cloud", "server", "database", "security", "firewall", "bug", "feature", "settings", "Bluetooth", "algorithm",
    ],
}


def translate_en_to_vi(text: str) -> str:
    if not text:
        return ""
    if GoogleTranslator is None:
        return ""
    try:
        return GoogleTranslator(source="en", target="vi").translate(text)
    except Exception:
        return ""


def meaning_vi_from_word(word: str) -> str:
    return translate_en_to_vi(word).strip()


def fetch_required_dictionary_fields(word: str) -> dict:
    try:
        encoded = quote(word.strip())
        res = requests.get(DICTIONARY_API.format(encoded), timeout=20)
        payload = res.json()
    except Exception:
        return {}

    if not isinstance(payload, list) or not payload:
        return {}

    entry = payload[0]

    phonetic = (entry.get("phonetic") or "").strip()
    audio = ""
    phonetics = entry.get("phonetics", []) or []

    for p in phonetics:
        if p.get("text") and not phonetic:
            phonetic = (p.get("text") or "").strip()
    for p in phonetics:
        if p.get("audio"):
            audio = (p.get("audio") or "").strip()
            if not phonetic and p.get("text"):
                phonetic = (p.get("text") or "").strip()
            break

    meanings = entry.get("meanings", []) or []
    part_of_speech = ""
    definition_en = ""
    if meanings:
        part_of_speech = (meanings[0].get("partOfSpeech") or "").strip()
        defs = meanings[0].get("definitions", []) or []
        if defs:
            definition_en = (defs[0].get("definition") or "").strip()

    if not (word and phonetic and audio and part_of_speech and definition_en):
        return {}

    return {
        "word": word,
        "phonetic": phonetic,
        "audio": audio,
        "part_of_speech": part_of_speech,
        "definition_en": definition_en,
    }


def build_inflection(word: str, part_of_speech: str) -> dict:
    pos = (part_of_speech or "").lower()
    if pos == "noun":
        plural = word + "s" if not word.endswith("s") else word
        return {"noun": {"singular": word, "plural": plural}}
    if pos == "verb":
        third = word + "s" if not word.endswith("s") else word
        past = word + "ed" if not word.endswith("e") else word + "d"
        ing = word + "ing" if not word.endswith("e") else word[:-1] + "ing"
        return {"verb": {"base": word, "third_person_singular": third, "past_simple": past, "present_participle": ing}}
    if pos == "adjective":
        return {"adjective": {"base": word}}
    return {pos or "other": {"base": word}}


def build_word_family(word: str) -> dict:
    base_meaning = meaning_vi_from_word(word)
    return {"base": {"word": word, "meaning_vi": base_meaning}}


def build_distractors(word: str, pool: list, k: int = 3) -> list:
    candidates = [w for w in pool if w != word]
    random.shuffle(candidates)
    return candidates[:k]


def build_examples(word: str, topic: str) -> list:
    if topic == "daily activities":
        sents = [
            f"I usually {word} before I start work.",
            f"On weekends, I try to {word} earlier.",
            f"I forgot to {word} this morning, so I felt rushed.",
        ]
    elif topic == "house and furniture":
        sents = [
            f"We bought a new {word} for the living room.",
            f"There's a {word} near the window where I like to sit and read.",
            f"Please put the {word} back after you use it.",
        ]
    elif topic == "weather":
        sents = [
            f"The weather {word} says it will rain in the afternoon.",
            f"It's {word} today, so bring a jacket.",
            f"Because of the {word}, flights were delayed.",
        ]
    elif topic == "shopping":
        sents = [
            f"Do you have the {word} for this purchase?",
            f"The store offered a {word} on all shoes.",
            f"I asked for a {word} because the item was damaged.",
        ]
    elif topic == "transportation":
        sents = [
            f"There was heavy {word} during rush hour.",
            f"We missed our {word}, so we had to wait for the next one.",
            f"Please check the {word} before you leave the station.",
        ]
    elif topic == "hobbies":
        sents = [
            f"I started {word} to relax after work.",
            f"{word.capitalize()} takes time, but it's really rewarding.",
            f"I joined a club to practice {word} with other people.",
        ]
    elif topic == "health":
        sents = [
            f"I booked an {word} with the doctor for tomorrow.",
            f"One common {word} is a high fever.",
            f"After the treatment, my {word} improved a lot.",
        ]
    elif topic == "emotions":
        sents = [
            f"I felt {word} before the exam.",
            f"She was {word} when she heard the good news.",
            f"Even though I was {word}, I tried to stay polite.",
        ]
    elif topic == "travel":
        sents = [
            f"Our {word} includes three cities in five days.",
            f"I made a {word} online and got a confirmation email.",
            f"We visited a famous {word} and took lots of photos.",
        ]
    elif topic == "technology":
        sents = [
            f"I installed a new {word} update last night.",
            f"Never share your {word} with anyone.",
            f"The app has a useful new {word} that saves time.",
        ]
    else:
        sents = [
            f"I learned the word '{word}' today.",
            f"Can you explain what '{word}' means?",
            f"Let's use '{word}' in a sentence.",
        ]

    examples = []
    for en in sents[:3]:
        vi = translate_en_to_vi(en).strip()
        if en.strip() and vi:
            examples.append({"en": en.strip(), "vi": vi})
    return examples


def complete_row(row: dict) -> bool:
    for k in ("word", "phonetic", "audio", "part_of_speech", "definition_en", "definition_vi", "meaning_vi"):
        v = row.get(k)
        if not isinstance(v, str) or not v.strip():
            return False
    if not isinstance(row.get("inflection"), dict) or not row["inflection"]:
        return False
    if not isinstance(row.get("word_family"), dict) or not row["word_family"]:
        return False
    examples = row.get("examples")
    if not isinstance(examples, list) or len(examples) != 3:
        return False
    distractors = row.get("distractors")
    if not isinstance(distractors, list) or len(distractors) != 3:
        return False
    for ex in examples:
        if not isinstance(ex, dict):
            return False
        if not ex.get("en") or not ex.get("vi"):
            return False
    return True


def try_build_row(word: str, topic: str, pool_for_distractors: list) -> dict:
    dic = fetch_required_dictionary_fields(word)
    if not dic:
        return {}

    definition_vi = translate_en_to_vi(dic["definition_en"]).strip()
    meaning_vi = meaning_vi_from_word(word)
    if not definition_vi or not meaning_vi:
        return {}

    inflection = build_inflection(word, dic["part_of_speech"])
    word_family = build_word_family(word)
    distractors = build_distractors(word, pool_for_distractors, k=3)
    if len(distractors) != 3:
        return {}

    examples = build_examples(word, topic)
    if len(examples) != 3:
        return {}

    row = {
        "word": dic["word"],
        "phonetic": dic["phonetic"],
        "audio": dic["audio"],
        "part_of_speech": dic["part_of_speech"],
        "definition_en": dic["definition_en"],
        "definition_vi": definition_vi,
        "meaning_vi": meaning_vi,
        "inflection": inflection,
        "word_family": word_family,
        "distractors": distractors,
        "examples": examples,
        "topic": topic,
        "level": LEVEL,
    }
    return row if complete_row(row) else {}


def main() -> None:
    rows = []
    skipped_topics = []

    for topic in TOPICS_IN_ORDER:
        pool = TOPIC_WORD_POOLS.get(topic, [])
        pool = [w.strip() for w in pool if isinstance(w, str) and w.strip()]
        if len(pool) < WORDS_PER_TOPIC + 3:
            skipped_topics.append(topic)
            continue

        pool_shuffled = pool[:]
        random.shuffle(pool_shuffled)

        accepted = []
        for w in pool_shuffled:
            if len(accepted) >= WORDS_PER_TOPIC:
                break
            row = try_build_row(w, topic, pool)
            if not row:
                continue
            accepted.append(row)

        if len(accepted) < WORDS_PER_TOPIC:
            skipped_topics.append(topic)
            continue

        rows.extend(accepted)

    if not rows:
        raise RuntimeError("No topics generated any valid rows.")

    excel_rows = []
    for r in rows:
        rr = dict(r)
        rr["inflection"] = json.dumps(rr["inflection"], ensure_ascii=False)
        rr["word_family"] = json.dumps(rr["word_family"], ensure_ascii=False)
        rr["distractors"] = json.dumps(rr["distractors"], ensure_ascii=False)
        rr["examples"] = json.dumps(rr["examples"], ensure_ascii=False)
        excel_rows.append(rr)

    df = pd.DataFrame(excel_rows)
    preferred_cols = [
        "word",
        "phonetic",
        "audio",
        "part_of_speech",
        "definition_en",
        "definition_vi",
        "meaning_vi",
        "inflection",
        "word_family",
        "distractors",
        "examples",
        "topic",
        "level",
    ]
    df = df[[c for c in preferred_cols if c in df.columns]]

    try:
        df.to_excel(OUTPUT_EXCEL, index=False)
        print(f"DONE! Saved: {OUTPUT_EXCEL} | rows: {len(df)}")
    except PermissionError:
        fallback = Path(
            f"{OUTPUT_EXCEL.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{OUTPUT_EXCEL.suffix}"
        )
        df.to_excel(fallback, index=False)
        print(f"DONE! Saved fallback: {fallback} | rows: {len(df)}")

    if skipped_topics:
        print("SKIPPED_TOPICS:", ", ".join(skipped_topics))


if __name__ == "__main__":
    main()

