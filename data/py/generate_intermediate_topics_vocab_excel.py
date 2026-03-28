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


OUTPUT_EXCEL = Path("vocab_intermediate_10topics_10words.xlsx")
DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{}"
LEVEL = "intermediate"
WORDS_PER_TOPIC = 10

TOPICS_IN_ORDER = [
    "environment",
    "education",
    "communication",
    "relationships",
    "business basics",
    "media & news",
    "culture",
    "sports",
    "internet & social media",
    "personal development",
]

# Larger pools to replace words that miss required API fields.
TOPIC_WORD_POOLS = {
    "environment": [
        "pollution", "recycling", "conservation", "ecosystem", "biodiversity", "habitat", "deforestation",
        "emissions", "carbon", "climate", "sustainability", "renewable", "solar", "wind", "compost",
        "wildlife", "endangered", "landfill", "waste", "resource", "drought", "flood", "greenhouse",
        "ocean", "plastic", "cleanup", "environmental", "preserve", "protect", "nature",
    ],
    "education": [
        "curriculum", "assignment", "lecture", "seminar", "tuition", "scholarship", "deadline", "research",
        "presentation", "participation", "attendance", "syllabus", "textbook", "revision", "assessment",
        "certificate", "degree", "graduate", "undergraduate", "department", "faculty", "principal",
        "mentor", "tutor", "discipline", "literacy", "knowledge", "skill", "evaluate", "feedback",
    ],
    "communication": [
        "conversation", "discussion", "debate", "explain", "clarify", "confirm", "suggest", "persuade",
        "negotiate", "interrupt", "respond", "reply", "message", "announcement", "feedback", "gesture",
        "expression", "tone", "context", "misunderstanding", "translate", "interpret", "summarize",
        "emphasize", "mention", "contact", "communicate", "email", "call", "text",
    ],
    "relationships": [
        "trust", "respect", "support", "commitment", "conflict", "compromise", "boundary", "apology",
        "forgive", "loyalty", "honesty", "friendship", "partner", "relationship", "breakup", "argument",
        "jealousy", "affection", "intimacy", "conversation", "understanding", "appreciate", "encourage",
        "betray", "reconcile", "dating", "marriage", "family", "together", "communication",
    ],
    "business basics": [
        "budget", "profit", "revenue", "expense", "invoice", "payment", "contract", "meeting",
        "proposal", "strategy", "customer", "client", "supplier", "purchase", "sale", "discount",
        "product", "service", "market", "brand", "competition", "deliver", "deadline", "estimate",
        "report", "salary", "schedule", "policy", "employee", "manager",
    ],
    "media & news": [
        "headline", "reporter", "journalist", "broadcast", "interview", "article", "coverage",
        "press", "statement", "source", "update", "breaking", "report", "evidence", "rumor",
        "verify", "fake", "bias", "opinion", "editor", "publish", "subscribe", "commentary",
        "documentary", "channel", "audience", "media", "news", "analysis", "investigation",
    ],
    "culture": [
        "tradition", "custom", "festival", "heritage", "identity", "community", "religion",
        "ceremony", "ritual", "celebration", "art", "music", "literature", "theater",
        "museum", "exhibition", "cuisine", "language", "values", "belief", "history",
        "ancient", "modern", "diversity", "cultural", "respect", "society", "symbol",
        "folklore", "craft",
    ],
    "sports": [
        "athlete", "training", "fitness", "strength", "stamina", "competition", "tournament",
        "champion", "coach", "referee", "score", "victory", "defeat", "practice",
        "injury", "recover", "strategy", "teamwork", "discipline", "performance",
        "endurance", "match", "league", "stadium", "spectator", "equipment",
        "warm-up", "stretch", "ranking", "goal",
    ],
    "internet & social media": [
        "platform", "profile", "account", "privacy", "security", "password", "settings",
        "notification", "comment", "message", "post", "share", "follow", "unfollow",
        "subscriber", "content", "creator", "viral", "hashtag", "algorithm",
        "stream", "upload", "download", "influencer", "community", "moderator",
        "report", "block", "spam", "trend",
    ],
    "personal development": [
        "habit", "routine", "discipline", "motivation", "mindset", "confidence", "self-esteem",
        "goal", "progress", "improve", "practice", "reflect", "feedback", "patience",
        "resilience", "focus", "productivity", "time management", "prioritize", "balance",
        "growth", "learn", "skill", "challenge", "commitment", "journal", "meditate",
        "stress", "healthy", "purpose",
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
        return {
            "verb": {
                "base": word,
                "third_person_singular": third,
                "past_simple": past,
                "present_participle": ing,
            }
        }
    if pos == "adjective":
        return {"adjective": {"base": word}}
    return {pos or "other": {"base": word}}


def build_word_family(word: str) -> dict:
    base_meaning = meaning_vi_from_word(word)
    return {"base": {"word": word, "meaning_vi": base_meaning}}


def build_distractors(word: str, pool: list, k: int = 3) -> list:
    candidates = [w for w in pool if w != word and " " not in w.strip()]
    random.shuffle(candidates)
    return candidates[:k]


def build_examples(word: str, topic: str) -> list:
    if topic == "environment":
        sents = [
            f"Plastic {word} is a serious problem in many cities.",
            f"We need to reduce carbon {word} to protect the climate.",
            f"The government launched a program to support {word}.",
        ]
    elif topic == "education":
        sents = [
            f"The teacher explained the {word} for the whole semester.",
            f"I submitted my {word} before the deadline.",
            f"Our {word} helped us understand the topic more deeply.",
        ]
    elif topic == "communication":
        sents = [
            f"Could you {word} what you mean in a simpler way?",
            f"We had a long {word} about the plan.",
            f"Her tone of voice changed the {word} of the message.",
        ]
    elif topic == "relationships":
        sents = [
            f"Trust is the foundation of any strong {word}.",
            f"They reached a {word} after a long argument.",
            f"He offered a sincere {word} and promised to change.",
        ]
    elif topic == "business basics":
        sents = [
            f"The company increased its {word} this quarter.",
            f"Please send the {word} to the finance department.",
            f"We discussed the {word} during the meeting.",
        ]
    elif topic == "media & news":
        sents = [
            f"The headline was shocking, but the full {word} was more balanced.",
            f"The reporter tried to {word} the story with two sources.",
            f"The channel provided live {word} of the event.",
        ]
    elif topic == "culture":
        sents = [
            f"The festival is an important cultural {word} for local people.",
            f"The museum showed an exhibition about national {word}.",
            f"Learning the language helps you understand the {word} better.",
        ]
    elif topic == "sports":
        sents = [
            f"Regular {word} improves your performance over time.",
            f"The team won the tournament after months of {word}.",
            f"He returned to the match quickly after the {word}.",
        ]
    elif topic == "internet & social media":
        sents = [
            f"She updated her {word} to make it more secure.",
            f"The post went {word} overnight and reached millions of people.",
            f"Turn off the {word} if you don't want alerts all day.",
        ]
    elif topic == "personal development":
        sents = [
            f"Building a good {word} takes time and consistency.",
            f"He set a clear {word} and tracked his progress weekly.",
            f"Learning to stay focused can boost your {word}.",
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
    if " " in word.strip():
        return {}
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
        pool = [w for w in pool if " " not in w]

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

