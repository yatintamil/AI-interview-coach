"""
Empathy and Sentiment Intelligence Engine.
Analyzes candidate responses to detect emotional state (anxious, hesitant, confident, confused, frustrated),
and synthesizes empathetic, Socratic coaching dialogue so the AI acts like a real-time human coach.
"""

import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

HESITANT_PATTERNS = [
    r"\b(i'm not sure|not really sure|i guess|maybe|perhaps|i think so|i don't know|not certain)\b",
    r"\b(could be|might be|probably|i believe so|possibly|um|uh|err)\b",
    r"\b(sorry|i might be wrong|if i recall correctly)\b",
]

CONFUSED_PATTERNS = [
    r"\b(what do you mean|can you clarify|confused|not sure what you're asking|a bit lost)\b",
    r"\b(don't understand|could you rephrase|unclear|which one)\b",
]

FRUSTRATED_PATTERNS = [
    r"\b(i have no idea|no clue|give up|skip this|too hard|impossible|can't do this)\b",
]

CONFIDENT_PATTERNS = [
    r"\b(specifically|in my experience|the primary trade-off|architecturally|first principles)\b",
    r"\b(i implemented|the key invariant|definitely|certainly|by design|measurably)\b",
    r"\b(the optimal approach|fundamentally|asymptotically|empirically)\b",
]


class EmpathyEngine:
    """
    Extracts emotional sentiment from candidate responses and generates
    supportive, human-like coaching dialogue and Socratic scaffolding.
    """

    @classmethod
    def analyze_candidate_emotion(
        cls,
        answer_text: str,
        response_time_seconds: Optional[float] = None,
        last_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Analyzes the emotional tone and feeling of the candidate's turn.
        """
        text = answer_text.strip().lower()
        word_count = len(text.split())

        # Match regex patterns
        hesitant_count = sum(len(re.findall(p, text)) for p in HESITANT_PATTERNS)
        confused_count = sum(len(re.findall(p, text)) for p in CONFUSED_PATTERNS)
        frustrated_count = sum(len(re.findall(p, text)) for p in FRUSTRATED_PATTERNS)
        confident_count = sum(len(re.findall(p, text)) for p in CONFIDENT_PATTERNS)

        tone = "neutral"
        intensity = "moderate"

        if frustrated_count > 0 or (word_count < 5 and any(w in text for w in ["skip", "no", "pass", "idk"])):
            tone = "frustrated"
            intensity = "high"
        elif confused_count > 0:
            tone = "confused"
            intensity = "high" if confused_count > 1 else "moderate"
        elif hesitant_count > 1 or (hesitant_count == 1 and word_count < 25):
            tone = "hesitant"
            intensity = "high" if hesitant_count > 2 else "moderate"
        elif confident_count >= 2 and hesitant_count == 0 and word_count > 35:
            tone = "confident"
            intensity = "high"
        elif word_count < 15 and (response_time_seconds and response_time_seconds > 45):
            tone = "anxious"
            intensity = "moderate"
        elif last_score is not None and last_score < 4.0 and word_count < 20:
            tone = "anxious"
            intensity = "moderate"

        dialogue = cls._generate_empathic_coach_dialogue(tone, intensity, answer_text)

        return {
            "tone": tone,
            "intensity": intensity,
            "detected_feeling": cls._get_feeling_label(tone, intensity),
            "coach_dialogue": dialogue["coach_message"],
            "socratic_scaffold": dialogue["scaffold"],
            "confidence_indicator": cls._get_confidence_meter(tone),
        }

    @classmethod
    def _get_feeling_label(cls, tone: str, intensity: str) -> str:
        labels = {
            "hesitant": "Hesitant & Deliberative 💭",
            "anxious": "Cautious / Under Pressure ⏳",
            "confused": "Seeking Clarity / Problem Framing 🧭",
            "frustrated": "Feeling Blocked / High Stress 🛑",
            "confident": "Decisive & Confident 🚀",
            "neutral": "Focused & Analytical ⚖️",
        }
        return labels.get(tone, "Reflective 💡")

    @classmethod
    def _get_confidence_meter(cls, tone: str) -> str:
        meters = {
            "confident": "High (Strong technical conviction)",
            "neutral": "Balanced (Objective technical framing)",
            "hesitant": "Moderate (Tentative exploration)",
            "anxious": "Low (Candidate feeling uncertain)",
            "confused": "Calibrating (Needs problem clarification)",
            "frustrated": "Recovering (Requires supportive reset)",
        }
        return meters.get(tone, "Balanced")

    @classmethod
    def _generate_empathic_coach_dialogue(
        cls, tone: str, intensity: str, answer_text: str
    ) -> Dict[str, str]:
        """
        Synthesizes human coaching conversational responses.
        """
        if tone == "hesitant":
            return {
                "coach_message": (
                    "I can sense a bit of hesitation here, which is completely natural! Engineering systems involve "
                    "complex trade-offs, and nobody has every single detail memorized. Take a breath—you're actually on "
                    "a sensible track. Let's break this down together."
                ),
                "scaffold": "Start by identifying the physical or logical constraint first, then step through what happens sequentially."
            }
        elif tone == "confused":
            return {
                "coach_message": (
                    "That's a very valid reaction—real engineering problems in production are rarely framed neatly in a textbook! "
                    "Let's reset the perspective and zoom in on the core goal."
                ),
                "scaffold": "Picture a minimal baseline scenario first: what is the simplest input and the desired output?"
            }
        elif tone == "frustrated":
            return {
                "coach_message": (
                    "Pause for a moment and shake that off—feeling stuck is an essential part of the problem-solving journey, "
                    "not a failure. Even senior principal architects run into walls. Let's take a step back and tackle it from a fresh angle."
                ),
                "scaffold": "Don't worry about complete perfection. Just tell me one first-principle fact you know about this component."
            }
        elif tone == "anxious":
            return {
                "coach_message": (
                    "You're doing great, and there is zero penalty for taking your time to think things through. "
                    "Interviews can feel intense, but remember: this is a collaborative technical dialogue, not an interrogation."
                ),
                "scaffold": "Think out loud freely. Sharing your intermediate thinking is often more valuable than an instantaneous answer."
            }
        elif tone == "confident":
            return {
                "coach_message": (
                    "Fantastic clarity and technical conviction! You articulated the underlying mechanics with precision. "
                    "Let's raise the stakes slightly and see how you stress-test that foundation."
                ),
                "scaffold": "Now consider what happens when constraints turn adverse: high scale, edge latency, or resource starvation."
            }
        else:
            return {
                "coach_message": (
                    "Appreciate the structured walkthrough. Let's examine how this connects to the broader system invariants."
                ),
                "scaffold": "Keep anchoring your reasoning back to foundational first principles."
            }
