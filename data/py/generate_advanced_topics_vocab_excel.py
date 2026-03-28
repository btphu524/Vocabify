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


OUTPUT_EXCEL = Path("vocab_advanced_10topics_10words.xlsx")
DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{}"
LEVEL = "advanced"
WORDS_PER_TOPIC = 10

TOPICS_IN_ORDER = [
    "academic vocabulary",
    "critical thinking",
    "artificial intelligence",
    "data science",
    "finance & investment",
    "marketing",
    "leadership",
    "innovation",
    "research & analysis",
    "abstract concepts",
]

TOPIC_WORD_POOLS = {
    "academic vocabulary": [
        "analyze", "synthesize", "evaluate", "interpret", "concept", "theory", "framework", "methodology",
        "hypothesis", "evidence", "argument", "assumption", "significant", "variable", "reliable",
        "valid", "objective", "subjective", "notion", "criterion", "perspective", "implication",
        "conclusion", "abstract", "context", "discipline", "literature", "citation", "reference", "research",
    ],
    "critical thinking": [
        "reasoning", "logic", "bias", "fallacy", "assumption", "evidence", "counterargument", "conclusion",
        "premise", "inference", "skepticism", "objectivity", "clarity", "consistency", "coherence",
        "evaluate", "analyze", "question", "justify", "verify", "assess", "interpret", "critique",
        "argument", "perspective", "judgment", "insight", "doubt", "rational", "reflect",
    ],
    "artificial intelligence": [
        "algorithm", "model", "dataset", "training", "prediction", "classification", "regression",
        "neural", "network", "optimization", "accuracy", "precision", "recall", "bias", "fairness",
        "inference", "automation", "robotics", "vision", "language", "transformer", "embedding",
        "prompt", "compute", "evaluation", "deployment", "monitoring", "privacy", "security", "explainability",
    ],
    "data science": [
        "statistics", "probability", "distribution", "correlation", "regression", "variance", "sampling",
        "dataset", "feature", "pipeline", "visualization", "dashboard", "outlier", "cleaning", "preprocess",
        "modeling", "validation", "metric", "insight", "forecast", "cluster", "classification",
        "experiment", "hypothesis", "analysis", "query", "database", "warehouse", "anomaly", "trend",
    ],
    "finance & investment": [
        "portfolio", "dividend", "equity", "bond", "yield", "interest", "inflation", "liquidity",
        "asset", "liability", "risk", "return", "volatility", "valuation", "capital", "leverage",
        "diversify", "allocate", "compound", "forecast", "margin", "profit", "revenue", "budget",
        "cashflow", "credit", "debt", "fund", "invest", "hedge",
    ],
    "marketing": [
        "brand", "audience", "segment", "target", "positioning", "campaign", "strategy", "channel",
        "content", "engagement", "conversion", "funnel", "analytics", "insight", "promotion",
        "pricing", "advertise", "organic", "paid", "traffic", "retention", "loyalty",
        "research", "survey", "competitor", "trend", "launch", "message", "value", "proposal",
    ],
    "leadership": [
        "vision", "strategy", "influence", "motivate", "delegate", "accountability", "integrity",
        "decision", "communication", "collaboration", "conflict", "coach", "mentor", "feedback",
        "performance", "responsibility", "initiative", "ownership", "trust", "culture",
        "alignment", "prioritize", "empower", "resilience", "commitment", "discipline", "adapt",
        "clarity", "governance", "stakeholder",
    ],
    "innovation": [
        "creative", "creativity", "prototype", "experiment", "iterate", "iteration", "design",
        "disrupt", "disruption", "breakthrough", "novel", "novelty", "idea", "concept",
        "solution", "problem", "opportunity", "risk", "venture", "startup",
        "scalable", "efficiency", "improve", "optimize", "transform", "adopt",
        "research", "development", "invention", "innovation",
    ],
    "research & analysis": [
        "research", "analyze", "analysis", "evidence", "method", "methodology", "survey", "interview",
        "observation", "experiment", "sample", "variable", "measure", "metric", "data",
        "validate", "reliable", "valid", "interpret", "summarize", "report",
        "conclusion", "finding", "insight", "trend", "pattern", "correlation", "causation",
        "hypothesis", "evaluate", "assess",
    ],
    "abstract concepts": [
        "freedom", "justice", "equality", "truth", "beauty", "meaning", "purpose", "identity",
        "morality", "ethics", "virtue", "rights", "dignity", "responsibility", "happiness",
        "knowledge", "wisdom", "belief", "faith", "conscience", "honor", "integrity",
        "peace", "love", "hope", "fear", "power", "time", "existence", "reality",
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
    if not word or " " in word.strip():
        return {}
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
    if topic == "academic vocabulary":
        sents = [
            f"The paper will {word} the main causes of the problem.",
            f"In the next section, we {word} the results and discuss implications.",
            f"The author uses evidence to {word} the claim.",
        ]
    elif topic == "critical thinking":
        sents = [
            f"Try to identify the hidden {word} in the argument.",
            f"We need stronger {word} before drawing a conclusion.",
            f"She challenged the claim by pointing out a logical {word}.",
        ]
    elif topic == "artificial intelligence":
        sents = [
            f"The {word} was trained on millions of examples.",
            f"A small {word} can reduce the model's accuracy.",
            f"They used the {word} to predict customer behavior.",
        ]
    elif topic == "data science":
        sents = [
            f"We removed an {word} that was skewing the analysis.",
            f"The team built a {word} to process data automatically.",
            f"The final report highlighted a clear {word} in the dataset.",
        ]
    elif topic == "finance & investment":
        sents = [
            f"A diversified {word} can reduce risk over time.",
            f"Rising {word} rates can affect borrowing costs.",
            f"Investors expect a higher {word} when risk increases.",
        ]
    elif topic == "marketing":
        sents = [
            f"The campaign improved brand {word} significantly.",
            f"We track {word} to understand how many visitors become customers.",
            f"The team refined the {word} to reach the right audience.",
        ]
    elif topic == "leadership":
        sents = [
            f"Good leaders {word} tasks clearly and follow up on progress.",
            f"She earned trust through consistent {word}.",
            f"Clear {word} helps teams avoid confusion and conflict.",
        ]
    elif topic == "innovation":
        sents = [
            f"They built a {word} to test the idea quickly.",
            f"After each experiment, they {word} the design based on feedback.",
            f"True {word} often comes from solving real problems.",
        ]
    elif topic == "research & analysis":
        sents = [
            f"The study used a small {word}, so the results are limited.",
            f"We {word} the data to find patterns and correlations.",
            f"The final {word} supports the original hypothesis.",
        ]
    elif topic == "abstract concepts":
        sents = [
            f"People often define {word} differently depending on culture and experience.",
            f"The debate focused on {word} and what it means in practice.",
            f"She valued {word} more than comfort or convenience.",
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

