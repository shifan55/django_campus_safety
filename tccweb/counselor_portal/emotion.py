"""Emotion and risk analysis helpers for counselor messaging."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean
from typing import Iterable, List, Sequence
import re

try:  # pragma: no cover - gracefully degrade if optional dependency missing
    from textblob import TextBlob
except Exception:  # pragma: no cover - TextBlob raises if corpora missing
    TextBlob = None


_ANXIOUS_PATTERNS = re.compile(
    r"\b(anxious|anxiety|panic|worried|worry|overwhelmed|uneasy|nervous)\b",
    re.IGNORECASE,
)
_ANGRY_PATTERNS = re.compile(
    r"\b(angry|furious|mad|rage|irritated|frustrated|upset|hate)\b",
    re.IGNORECASE,
)
_STRESSED_PATTERNS = re.compile(
    r"\b(stress(ed|ful)?|pressure|burn(out|ed)|tired|exhausted)\b",
    re.IGNORECASE,
)
_CALM_PATTERNS = re.compile(
    r"\b(relieved|better now|okay|fine|calm|breathing|managing)\b",
    re.IGNORECASE,
)
_CRITICAL_PATTERNS = re.compile(
    r"\b(suicid(e|al)|kill myself|self-harm|end my life|hurt myself|give up|no reason to live)\b",
    re.IGNORECASE,
)


EMOTION_LABELS = {
    "anxious": "Anxious",
    "angry": "Angry",
    "stressed": "Stressed",
    "calm": "Calm",
    "neutral": "Neutral",
}

RISK_LEVELS = {
    "normal": "Stable",
    "elevated": "Elevated",
    "critical": "Critical",
}


@dataclass(frozen=True)
class EmotionInsight:
    """Structured output describing how a message feels."""

    label: str
    confidence: float
    polarity: float
    risk_level: str
    explanation: str

    @property
    def display_label(self) -> str:
        return EMOTION_LABELS.get(self.label, self.label.title())

    @property
    def display_risk(self) -> str:
        return RISK_LEVELS.get(self.risk_level, self.risk_level.title())


def _blob_sentiment(text: str) -> float:
    if not TextBlob:
        return 0.0
    try:
        return float(TextBlob(text).sentiment.polarity)
    except Exception:  # pragma: no cover - TextBlob may fail without corpora
        return 0.0


def _mean_sentiment(samples: Iterable[str]) -> float:
    scores: List[float] = [score for text in samples if (score := _blob_sentiment(text))]
    if not scores:
        return 0.0
    return float(fmean(scores))


def analyze_emotion(message: str, *, context: Sequence[str] | None = None) -> EmotionInsight:
    """Analyze a message and optional history for emotional cues."""

    context = [c for c in (context or []) if c]
    message = (message or "").strip()
    combined_context = " \n".join(context)

    polarity = _blob_sentiment(message)
    contextual_polarity = _mean_sentiment([combined_context]) if combined_context else polarity

    # Weight contextual polarity so sustained negativity increases risk
    blended_polarity = (polarity * 0.7) + (contextual_polarity * 0.3)

    text_for_patterns = f"{combined_context} \n {message}" if combined_context else message

    label = "neutral"
    explanation: List[str] = []

    if _CRITICAL_PATTERNS.search(text_for_patterns):
        label = "stressed"
        explanation.append("Detected urgent language indicating potential self-harm risk.")
    elif _ANXIOUS_PATTERNS.search(text_for_patterns):
        label = "anxious"
        explanation.append("Student referenced anxiety or worry cues.")
    elif _ANGRY_PATTERNS.search(text_for_patterns):
        label = "angry"
        explanation.append("Language suggests frustration or anger.")
    elif _STRESSED_PATTERNS.search(text_for_patterns):
        label = "stressed"
        explanation.append("Stress or burnout phrases detected.")
    elif _CALM_PATTERNS.search(text_for_patterns):
        label = "calm"
        explanation.append("Student explicitly described feeling calmer.")
    else:
        if blended_polarity > 0.25:
            label = "calm"
            explanation.append("Overall positive tone across the conversation.")
        elif blended_polarity < -0.2:
            label = "anxious"
            explanation.append("Negative tone suggests heightened concern.")

    risk_level = "normal"

    if _CRITICAL_PATTERNS.search(text_for_patterns):
        risk_level = "critical"
    elif blended_polarity < -0.45:
        risk_level = "critical"
        explanation.append("Severely negative tone detected across messages.")
    elif blended_polarity < -0.25 or label in {"anxious", "stressed"}:
        risk_level = "elevated"
        if not explanation:
            explanation.append("Sustained worry or stress detected in context.")

    confidence_base = max(abs(blended_polarity), 0.2)
    keyword_boost = 0.35 if explanation else 0.0
    confidence = min(0.95, 0.4 + keyword_boost + confidence_base * 0.4)

    return EmotionInsight(
        label=label,
        confidence=round(confidence, 3),
        polarity=round(blended_polarity, 3),
        risk_level=risk_level,
        explanation=" ".join(explanation) if explanation else "Tone inferred from overall sentiment cues.",
    )