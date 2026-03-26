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


OUTPUT_EXCEL = Path("vocab_easy_10topics_10words.xlsx")
DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{}"
LEVEL = "easy"
WORDS_PER_TOPIC = 10

TOPICS_IN_ORDER = [
    "animals",
    "family",
    "colors",
    "food and drinks",
    "body parts",
    "school",
    "jobs",
    "days and months",
    "clothes",
    "numbers",
]

# Larger pools to allow replacing words that miss required API fields.
TOPIC_WORD_POOLS = {
    "animals": [
        "cat", "dog", "lion", "tiger", "elephant", "giraffe", "zebra", "rabbit", "monkey", "bear",
        "horse", "cow", "goat", "sheep", "pig", "duck", "chicken", "bird", "fish", "mouse",
        "wolf", "fox", "deer", "camel", "snake", "turtle", "frog", "bee", "spider", "whale",
        "dolphin", "shark", "owl", "eagle", "parrot", "squirrel", "hamster", "panda", "kangaroo", "crocodile",
    ],
    "family": [
        "mother", "father", "parent", "brother", "sister", "son", "daughter", "child", "baby", "family",
        "grandmother", "grandfather", "uncle", "aunt", "husband", "wife", "nephew", "niece", "relatives", "parents",
        "children", "spouse", "twin", "grandson", "granddaughter", "teenager",
    ],
    "colors": [
        "red", "blue", "green", "yellow", "black", "white", "orange", "purple", "pink", "brown",
        "gray", "gold", "silver", "dark", "light", "bright", "pale", "navy", "violet", "beige",
        "turquoise", "amber", "maroon",
    ],
    "food and drinks": [
        "rice", "bread", "noodle", "soup", "meat", "fish", "egg", "milk", "water", "juice",
        "tea", "coffee", "cake", "apple", "banana", "sugar", "salt", "breakfast", "dinner", "cheese",
        "honey", "sandwich", "salad", "cookie", "candy", "yogurt",
    ],
    "body parts": [
        "head", "face", "eye", "ear", "nose", "mouth", "tooth", "neck", "shoulder", "arm",
        "hand", "finger", "leg", "knee", "foot", "toe", "back", "heart", "stomach", "hair",
        "skin", "tongue", "lip", "elbow", "wrist", "ankle",
    ],
    "school": [
        "school", "class", "teacher", "student", "book", "pen", "pencil", "ruler", "desk", "chair",
        "lesson", "exam", "test", "question", "answer", "library", "paper", "calculator", "dictionary", "subject",
        "grade", "backpack", "principal",
    ],
    "jobs": [
        "doctor", "nurse", "teacher", "farmer", "driver", "chef", "police", "soldier", "engineer", "worker",
        "manager", "pilot", "artist", "actor", "writer", "lawyer", "dentist", "mechanic", "journalist", "barber",
        "plumber", "musician",
    ],
    "days and months": [
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        "january", "february", "march", "april", "may", "june", "july", "august",
        "september", "october", "november", "december", "month",
        "today", "tomorrow", "yesterday", "morning", "evening", "night",
        "weekend", "weekday", "year", "date", "calendar", "hour", "minute", "season",
        "spring", "summer", "autumn", "winter",
    ],
    "clothes": [
        "shirt", "dress", "skirt", "jeans", "pants", "jacket", "coat", "sweater", "shoe", "sock",
        "hat", "cap", "belt", "scarf", "glove", "uniform", "pocket", "button", "boot", "tie",
        "watch", "hoodie", "vest", "pajamas",
    ],
    "numbers": [
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "twenty", "thirty", "forty", "fifty",
        "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "first", "second",
    ],
}

REQUIRED_DIC_FIELDS = ("phonetic", "audio", "part_of_speech", "definition_en")


def translate_en_to_vi(text: str) -> str:
    if not text:
        return ""
    if GoogleTranslator is None:
        return ""
    return GoogleTranslator(source="en", target="vi").translate(text)


def fetch_required_dictionary_fields(word: str) -> dict:
    encoded = quote(word.strip())
    res = requests.get(DICTIONARY_API.format(encoded), timeout=20)
    payload = res.json()

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


def meaning_vi_from_word(word: str) -> str:
    # Direct lexical translation (best effort).
    return translate_en_to_vi(word).strip()


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


def build_word_family(word: str, topic: str) -> dict:
    # For easy-level data: keep a small, safe family set.
    base = {"word": word, "meaning_vi": meaning_vi_from_word(word)}
    family = {"base": base}

    # Topic-specific additions that are generally correct.
    if topic == "animals" and word == "cat":
        family.update(
            {
                "kitten": {"word": "kitten", "meaning_vi": "mèo con"},
                "tomcat": {"word": "tomcat", "meaning_vi": "mèo đực"},
            }
        )
    if topic == "family" and word in ("mother", "father"):
        family.update({"parent": {"word": "parent", "meaning_vi": "cha hoặc mẹ; phụ huynh"}})

    return family


def build_distractors(word: str, pool: list, k: int = 3) -> list:
    candidates = [w for w in pool if w != word]
    random.shuffle(candidates)
    return candidates[:k]


def build_examples(word: str, topic: str) -> list:
    # 3 examples with different contexts and structures per topic
    if topic == "animals":
        examples = [
            {"en": f"The {word} is sleeping under the tree.", "vi": translate_en_to_vi(f"The {word} is sleeping under the tree.")},
            {"en": f"I saw a {word} at the zoo yesterday.", "vi": translate_en_to_vi(f"I saw a {word} at the zoo yesterday.")},
            {"en": f"Be careful—this {word} can be dangerous.", "vi": translate_en_to_vi(f"Be careful—this {word} can be dangerous.")},
        ]
    elif topic == "food and drinks":
        examples = [
            {"en": f"I usually have {word} for breakfast.", "vi": translate_en_to_vi(f"I usually have {word} for breakfast.")},
            {"en": f"Could I get some {word}, please?", "vi": translate_en_to_vi(f"Could I get some {word}, please?")},
            {"en": f"This {word} tastes really good.", "vi": translate_en_to_vi(f"This {word} tastes really good.")},
        ]
    elif topic == "school":
        examples = [
            {"en": f"I forgot my {word} at home.", "vi": translate_en_to_vi(f"I forgot my {word} at home.")},
            {"en": f"Our teacher gave us a {word} today.", "vi": translate_en_to_vi(f"Our teacher gave us a {word} today.")},
            {"en": f"Please open your {word} and read the first page.", "vi": translate_en_to_vi(f"Please open your {word} and read the first page.")},
        ]
    elif topic == "jobs":
        examples = [
            {"en": f"My aunt is a {word}.", "vi": translate_en_to_vi(f"My aunt is a {word}.")},
            {"en": f"A {word} works hard every day.", "vi": translate_en_to_vi(f"A {word} works hard every day.")},
            {"en": f"I want to be a {word} in the future.", "vi": translate_en_to_vi(f"I want to be a {word} in the future.")},
        ]
    else:
        examples = [
            {"en": f"Do you know the word '{word}'?", "vi": translate_en_to_vi(f"Do you know the word '{word}'?")},
            {"en": f"Can you spell {word}?", "vi": translate_en_to_vi(f"Can you spell {word}?")},
            {"en": f"We learned {word} today.", "vi": translate_en_to_vi(f"We learned {word} today.")},
        ]

    # Ensure non-empty Vietnamese for all examples
    cleaned = []
    for ex in examples:
        en = (ex.get("en") or "").strip()
        vi = (ex.get("vi") or "").strip()
        if en and vi:
            cleaned.append({"en": en, "vi": vi})
    return cleaned


def complete_row(row: dict) -> bool:
    for k in ("word", "phonetic", "audio", "part_of_speech", "definition_en", "definition_vi", "meaning_vi"):
        v = row.get(k)
        if not isinstance(v, str) or not v.strip():
            return False
    examples = row.get("examples")
    distractors = row.get("distractors")
    if not isinstance(examples, list) or len(examples) != 3:
        return False
    if not isinstance(distractors, list) or len(distractors) != 3:
        return False
    if not isinstance(row.get("inflection"), dict) or not row["inflection"]:
        return False
    if not isinstance(row.get("word_family"), dict) or not row["word_family"]:
        return False
    return True


def try_build_row(word: str, topic: str, pool_for_distractors: list) -> dict:
    dic = fetch_required_dictionary_fields(word)
    if not dic:
        return {}

    definition_vi = translate_en_to_vi(dic["definition_en"]).strip()
    meaning_vi = meaning_vi_from_word(word)
    inflection = build_inflection(word, dic["part_of_speech"])
    word_family = build_word_family(word, topic)
    distractors = build_distractors(word, pool_for_distractors, k=3)
    examples = build_examples(word, topic)

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

    if not complete_row(row):
        return {}
    return row


def main() -> None:
    rows = []
    skipped_topics = []

    for topic in TOPICS_IN_ORDER:
        pool = TOPIC_WORD_POOLS.get(topic, [])
        pool = [w.strip() for w in pool if isinstance(w, str) and w.strip()]
        if len(pool) < WORDS_PER_TOPIC + 3:
            skipped_topics.append(topic)
            continue

        # Keep order but shuffle a bit so replacement happens naturally.
        pool_shuffled = pool[:]
        random.shuffle(pool_shuffled)

        accepted = []
        tried = 0
        for w in pool_shuffled:
            if len(accepted) >= WORDS_PER_TOPIC:
                break
            tried += 1
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

    # Convert complex fields to JSON strings for Excel cells.
    excel_rows = []
    for r in rows:
        rr = dict(r)
        rr["inflection"] = json.dumps(rr["inflection"], ensure_ascii=False)
        rr["word_family"] = json.dumps(rr["word_family"], ensure_ascii=False)
        rr["distractors"] = json.dumps(rr["distractors"], ensure_ascii=False)
        rr["examples"] = json.dumps(rr["examples"], ensure_ascii=False)

        # Ensure topic + level are at the end by ordering columns later.
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

