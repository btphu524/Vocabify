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


OUTPUT_EXCEL = Path("example.xlsx")
DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{}"
LEVEL = "easy"
WORDS_PER_TOPIC = 20

# Preferred order first; script skips words that fail strict completeness and takes more from the tail.
TOPIC_WORD_POOLS = {
    "animals": [
        "cat", "dog", "lion", "tiger", "elephant", "giraffe", "zebra", "rabbit", "monkey", "bear",
        "horse", "cow", "goat", "sheep", "pig", "duck", "chicken", "bird", "fish", "mouse",
        "wolf", "fox", "deer", "camel", "snake", "turtle", "frog", "bee", "spider", "whale",
        "dolphin", "shark", "owl", "eagle", "parrot", "squirrel", "hamster", "panda", "kangaroo", "crocodile",
    ],
    "family": [
        "mother", "father", "parent", "brother", "sister", "son", "daughter", "child", "baby", "grandmother",
        "grandfather", "grandparent", "uncle", "aunt", "cousin", "husband", "wife", "family", "nephew", "niece",
        "parents", "children", "siblings", "spouse", "relatives", "in-laws", "stepfather", "stepmother", "orphan", "widow",
    ],
    "numbers": [
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "twenty", "thirty", "hundred", "thousand",
        "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "million", "billion", "first", "second",
    ],
    "colors": [
        "red", "blue", "green", "yellow", "black", "white", "orange", "purple", "pink", "brown",
        "gray", "gold", "silver", "dark", "light", "color", "bright", "pale", "clear", "rainbow",
        "violet", "beige", "navy", "maroon", "turquoise", "crimson", "amber", "magenta", "khaki", "cyan",
    ],
    "food and drinks": [
        "rice", "bread", "noodle", "soup", "meat", "fish", "egg", "milk", "water", "juice",
        "tea", "coffee", "cake", "apple", "banana", "orange", "sugar", "salt", "breakfast", "dinner",
        "cheese", "butter", "honey", "sandwich", "pizza", "burger", "salad", "cookie", "candy", "yogurt",
    ],
    "body parts": [
        "head", "face", "eye", "ear", "nose", "mouth", "tooth", "neck", "shoulder", "arm",
        "hand", "finger", "leg", "knee", "foot", "toe", "back", "heart", "stomach", "hair",
        "elbow", "wrist", "ankle", "chin", "cheek", "tongue", "lip", "lung", "liver", "skin",
    ],
    "clothes": [
        "shirt", "t-shirt", "dress", "skirt", "jeans", "pants", "shorts", "jacket", "coat", "sweater",
        "shoe", "sock", "hat", "cap", "belt", "scarf", "glove", "uniform", "pocket", "button",
        "boot", "sneaker", "sandals", "tie", "vest", "hoodie", "blouse", "underwear", "pajamas", "watch",
    ],
    "days and months": [
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "january", "february", "march",
        "april", "may", "june", "july", "august", "september", "october", "november", "december", "month",
        "weekend", "weekday", "today", "tomorrow", "yesterday", "morning", "evening", "season", "spring", "autumn",
        "year", "night", "noon", "midnight", "calendar", "clock", "minute", "hour", "date", "holiday",
        "birthday", "anniversary", "schedule", "daily", "weekly", "monthly", "annual", "winter", "summer", "fall",
        "century", "decade", "moment", "period", "timeline", "appointment", "deadline", "vacation", "festival", "era",
    ],
    "school": [
        "school", "class", "teacher", "student", "book", "notebook", "pen", "pencil", "eraser", "ruler",
        "desk", "chair", "board", "lesson", "homework", "exam", "test", "question", "answer", "library",
        "backpack", "marker", "crayon", "paper", "glue", "calculator", "dictionary", "principal", "subject", "grade",
    ],
    "jobs": [
        "doctor", "nurse", "teacher", "student", "farmer", "driver", "chef", "police", "soldier", "engineer",
        "worker", "manager", "seller", "cashier", "pilot", "artist", "actor", "writer", "lawyer", "job",
        "dentist", "scientist", "musician", "journalist", "mechanic", "plumber", "electrician", "designer", "photographer", "barber",
    ],
}

# Fields that must be non-empty for a word to be kept (synonyms/antonyms/inflection/word_family may stay empty -> omitted from row as null).
REQUIRED_DICTIONARY_STRING_FIELDS = (
    "phonetic",
    "audio",
    "part_of_speech",
    "definition_en",
    "definition_vi",
    "meaning_vi",
)


def safe_translate_en_to_vi(text: str):
    if not text:
        return None
    if GoogleTranslator is None:
        return text
    try:
        return GoogleTranslator(source="en", target="vi").translate(text)
    except Exception:
        return None


def get_meaning_vi(word: str):
    return safe_translate_en_to_vi(word) if word else None


def noun_plural(word: str) -> str:
    if word.endswith(("s", "x", "z", "ch", "sh")):
        return f"{word}es"
    if word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou":
        return f"{word[:-1]}ies"
    return f"{word}s"


def verb_forms(word: str) -> dict:
    if word.endswith("e"):
        past = f"{word}d"
        ing = f"{word[:-1]}ing"
    elif word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou":
        past = f"{word[:-1]}ied"
        ing = f"{word}ing"
    else:
        past = f"{word}ed"
        ing = f"{word}ing"

    if word.endswith(("s", "x", "z", "ch", "sh", "o")):
        third = f"{word}es"
    elif word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou":
        third = f"{word[:-1]}ies"
    else:
        third = f"{word}s"

    return {
        "base": word,
        "third_person_singular": third,
        "past_simple": past,
        "past_participle": past,
        "present_participle": ing,
    }


def adjective_forms(word: str) -> dict:
    if len(word) <= 2:
        return {"base": word, "comparative": f"more {word}", "superlative": f"most {word}"}
    if word.endswith("y"):
        return {"base": word, "comparative": f"{word[:-1]}ier", "superlative": f"{word[:-1]}iest"}
    if word.endswith("e"):
        return {"base": word, "comparative": f"{word}r", "superlative": f"{word}st"}
    return {"base": word, "comparative": f"more {word}", "superlative": f"most {word}"}


def build_inflections(word: str, pos_set: set):
    inflections = {}
    if "noun" in pos_set:
        inflections["noun"] = {"singular": word, "plural": noun_plural(word)}
    if "verb" in pos_set:
        inflections["verb"] = verb_forms(word)
    if "adjective" in pos_set:
        inflections["adjective"] = adjective_forms(word)
    if "adverb" in pos_set:
        inflections["adverb"] = {"base": word}
    return inflections if inflections else None


def fetch_dictionary_data(word: str) -> dict:
    try:
        encoded = quote(word.strip())
        response = requests.get(DICTIONARY_API.format(encoded), timeout=20)
        payload = response.json()
    except Exception:
        return {}
    if not isinstance(payload, list) or not payload:
        return {}

    entry = payload[0]
    phonetic = (entry.get("phonetic") or "").strip()
    audio = ""
    phonetics = entry.get("phonetics", [])
    for p in phonetics:
        if p.get("text") and not phonetic:
            phonetic = (p.get("text") or "").strip()
    for p in phonetics:
        if p.get("audio"):
            audio = (p.get("audio") or "").strip()
            if not phonetic and p.get("text"):
                phonetic = (p.get("text") or "").strip()
            break

    meanings = entry.get("meanings", [])
    if not meanings:
        return {}

    primary_pos = meanings[0].get("partOfSpeech", "")
    definition_en = ""
    synonyms = []
    antonyms = []
    pos_set = set()
    pos_variants = []

    for meaning in meanings:
        pos = meaning.get("partOfSpeech", "")
        if pos:
            pos_set.add(pos)
            pos_variants.append({"part_of_speech": pos, "word": word})
        synonyms.extend(meaning.get("synonyms", []))
        antonyms.extend(meaning.get("antonyms", []))
        defs = meaning.get("definitions", [])
        if defs and not definition_en:
            definition_en = defs[0].get("definition", "")
        if defs:
            synonyms.extend(defs[0].get("synonyms", []))
            antonyms.extend(defs[0].get("antonyms", []))

    return {
        "phonetic": phonetic or None,
        "audio": audio or None,
        "part_of_speech": primary_pos or None,
        "definition_en": definition_en or None,
        "definition_vi": safe_translate_en_to_vi(definition_en) if definition_en else None,
        "meaning_vi": get_meaning_vi(word),
        "synonyms": {"items": sorted(set([x for x in synonyms if x]))} if synonyms else None,
        "antonyms": {"items": sorted(set([x for x in antonyms if x]))} if antonyms else None,
        "inflection": build_inflections(word, pos_set),
        "word_other_pos_forms": pos_variants if pos_variants else None,
    }


def make_short_examples(word: str):
    # Keep examples natural while avoiding extra API translation calls.
    return [
        {"en": f"I see a {word} every day.", "vi": f"Tôi thấy {word} mỗi ngày."},
        {"en": f"This {word} is very nice.", "vi": f"{word.capitalize()} này rất dễ thương."},
        {"en": f"We learned the word {word} in class.", "vi": f"Chúng tôi học từ {word} ở lớp."},
    ]


def build_word_family(word: str, pos_set_like: list):
    if not pos_set_like:
        return None
    pos_names = {x.get("part_of_speech") for x in pos_set_like if x.get("part_of_speech")}
    family = {}
    if "noun" in pos_names:
        family["noun"] = word
    if "verb" in pos_names:
        family["verb"] = word
    if "adjective" in pos_names:
        family["adjective"] = word
    if "adverb" in pos_names:
        family["adverb"] = word
    return family if family else None


def build_distractors(current_word: str, topic_words: list, limit: int = 3):
    pool = [w for w in topic_words if w != current_word]
    if len(pool) < limit:
        return None
    random.shuffle(pool)
    return {"choices": pool[:limit]}


def build_common_mistakes(word: str):
    return {
        "items": [
            f"Spelling '{word}' incorrectly.",
            f"Using '{word}' in a wrong context.",
        ]
    }


def build_mnemonic(word: str, meaning_vi: str):
    if not meaning_vi:
        return None
    return {"text": f"Imagine '{word}' clearly. Repeat: {word} = {meaning_vi}."}


def build_tags(topic: str, pos: str, level: str):
    tags = ["vocabify", topic, level]
    if pos:
        tags.append(pos)
    return tags


def _nonempty_str(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def dictionary_row_complete(dic: dict) -> bool:
    if not dic:
        return False
    for key in REQUIRED_DICTIONARY_STRING_FIELDS:
        if not _nonempty_str(dic.get(key)):
            return False
    return True


def examples_complete(examples: list) -> bool:
    if not examples or len(examples) < 3:
        return False
    for item in examples:
        if not _nonempty_str(item.get("en")) or not _nonempty_str(item.get("vi")):
            return False
    return True


def unique_preserve_order(words: list) -> list:
    seen = set()
    out = []
    for w in words:
        w = (w or "").strip()
        if not w or w in seen:
            continue
        seen.add(w)
        out.append(w)
    return out


def collect_topic_entries(topic: str, pool: list) -> list:
    """Up to WORDS_PER_TOPIC (word, dic) pairs; skips incomplete words, tries further pool items."""
    accepted = []
    used = set()
    for word in pool:
        if len(accepted) >= WORDS_PER_TOPIC:
            break
        if word in used:
            continue
        used.add(word)
        try:
            dic = fetch_dictionary_data(word)
        except Exception as exc:
            print(f"SKIP {topic}: {word} (error: {exc})")
            continue
        if not dictionary_row_complete(dic):
            print(f"SKIP {topic}: {word} (incomplete dictionary / translation)")
            continue
        examples = make_short_examples(word)
        if not examples_complete(examples):
            print(f"SKIP {topic}: {word} (incomplete examples)")
            continue
        if not build_mnemonic(word, dic["meaning_vi"]):
            print(f"SKIP {topic}: {word} (no mnemonic)")
            continue
        accepted.append((word, dic))
        print(f"OK {topic} {len(accepted)}/{WORDS_PER_TOPIC}: {word}")
    return accepted


def main():
    records = []

    for topic, raw_pool in TOPIC_WORD_POOLS.items():
        pool = unique_preserve_order(raw_pool)
        random.shuffle(pool)
        entries = collect_topic_entries(topic, pool)
        if len(entries) < WORDS_PER_TOPIC:
            print(
                f"WARNING {topic}: only {len(entries)}/{WORDS_PER_TOPIC} words met strict requirements. "
                "Add more words to TOPIC_WORD_POOLS for this topic."
            )

        final_words = [w for w, _ in entries]
        if len(final_words) < 4:
            print(
                f"WARNING {topic}: only {len(final_words)} accepted words; need >=4 for distractors. "
                "Skipping export for this topic."
            )
            continue

        for word, dic in entries:
            examples = make_short_examples(word)
            word_family = build_word_family(word, dic["word_other_pos_forms"])
            distractors = build_distractors(word, final_words)
            common_mistakes = build_common_mistakes(word)
            mnemonic = build_mnemonic(word, dic["meaning_vi"])
            tags = build_tags(topic, dic["part_of_speech"], LEVEL)

            if distractors is None or mnemonic is None:
                raise RuntimeError(f"Internal: distractors/mnemonic missing for {topic}/{word}")

            records.append(
                {
                    "word": word,
                    "phonetic": dic["phonetic"],
                    "part_of_speech": dic["part_of_speech"],
                    "definition_en": dic["definition_en"],
                    "definition_vi": dic["definition_vi"],
                    "meaning_vi": dic["meaning_vi"],
                    "synonyms": json.dumps(dic["synonyms"], ensure_ascii=False) if dic["synonyms"] else None,
                    "antonyms": json.dumps(dic["antonyms"], ensure_ascii=False) if dic["antonyms"] else None,
                    "audio": dic["audio"],
                    "inflection": json.dumps(dic["inflection"], ensure_ascii=False) if dic["inflection"] else None,
                    "word_other_pos_forms": json.dumps(dic["word_other_pos_forms"], ensure_ascii=False)
                    if dic["word_other_pos_forms"]
                    else None,
                    "examples": json.dumps(examples, ensure_ascii=False),
                    "word_family": json.dumps(word_family, ensure_ascii=False) if word_family else None,
                    "distractors": json.dumps(distractors, ensure_ascii=False),
                    "common_mistakes": json.dumps(common_mistakes, ensure_ascii=False),
                    "mnemonic": json.dumps(mnemonic, ensure_ascii=False),
                    "tags": json.dumps(tags, ensure_ascii=False),
                    "topic": topic,
                    "level": LEVEL,
                }
            )

    df = pd.DataFrame(records)
    try:
        df.to_excel(OUTPUT_EXCEL, index=False)
        print(f"DONE! Saved: {OUTPUT_EXCEL} | total rows: {len(df)}")
    except PermissionError:
        fallback = Path(f"{OUTPUT_EXCEL.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{OUTPUT_EXCEL.suffix}")
        df.to_excel(fallback, index=False)
        print(f"DONE! Saved fallback: {fallback} | total rows: {len(df)}")


if __name__ == "__main__":
    main()
