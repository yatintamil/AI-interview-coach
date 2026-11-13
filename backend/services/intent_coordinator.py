"""
Deterministic and Semantic Intent Coordinator for Conversational Routing.
Classifies user messages into categorical intents without requiring paid LLM APIs,
falling back gracefully to GENERAL_CHAT while guaranteeing deterministic action routing.
"""

import re
from typing import Optional, Tuple
from backend.schemas.chat import ChatIntent


class IntentCoordinator:
    """
    Lightweight, provider-independent intent classification coordinator.
    Prioritizes deterministic keyword and regex heuristics for system actions
    (interview, evaluation, roadmap, transfer, coaching) to guarantee reproducible
    orchestration without hallucination.
    """

    # Deterministic pattern matching rules
    INTENT_PATTERNS = [
        # Transfer & Unseen Challenges
        (
            ChatIntent.TRANSFER,
            r"\b(transfer|unseen|unfamiliar|new problem|new challenge|challenge me|another challenge|without help|test me on (a )?new|harder problem|different domain)\b",
        ),
        # Coaching & Hints
        (
            ChatIntent.COACHING,
            r"\b(coach( me)?|coaching|hint|clue|help me|guide me|socratic|scaffold|stuck|give me a hint|teach me my weakest|try again|retry|one more try|another try)\b",
        ),
        # Evaluation & Mistake Explanation
        (
            ChatIntent.EVALUATION,
            r"\b(evaluate( my)?|check my answer|review my answer|score my|why (is )?my answer (wrong|incorrect)|am i correct)\b",
        ),
        # Full Mock Interview & Practice
        (
            ChatIntent.INTERVIEW,
            r"\b(mock interview|start interview|interview me|practice question|give me (a|another) question|another question|next question|test my skills|interview practice)\b",
        ),
        # Skill Gap & Weakness Analysis
        (
            ChatIntent.SKILL_GAP,
            r"\b(my weakest|weakness(es)?|weak areas?|skill gap|what should i improve|competency delta|areas for improvement)\b",
        ),
        # Roadmap & Milestones
        (
            ChatIntent.ROADMAP,
            r"\b(roadmap|learning plan|milestone|study plan|what to study next|curriculum)\b",
        ),
        # Session Status & Progress Tracking
        (
            ChatIntent.SESSION_STATUS,
            r"\b(progress|my score|how am i doing|learning progress|mastery level|radar chart|stats)\b",
        ),
    ]

    @classmethod
    def classify_intent(cls, message: str, active_state: Optional[str] = None) -> ChatIntent:
        """
        Classifies incoming conversational input into a domain intent.
        
        Args:
            message: Raw user message string.
            active_state: Optional current state (e.g. 'INTERVIEW_PENDING', 'COACHING_TRANSFER').
        
        Returns:
            ChatIntent enum value.
        """
        if not message or not message.strip():
            return ChatIntent.GENERAL_CHAT

        text = message.lower().strip()

        # Context-dependent priority: if an active evaluation or question was posed
        if active_state in ("AWAITING_ANSWER", "QUESTION_ACTIVE", "COACHING_ACTIVE"):
            # If the user asks for a hint explicitly or asks to retry, route to COACHING
            if re.search(r"\b(hint|help|clue|stuck|try again|retry)\b", text):
                return ChatIntent.COACHING
            # Otherwise, substantial answer submission defaults to EVALUATION
            if len(text.split()) >= 3 and active_state == "AWAITING_ANSWER":
                return ChatIntent.EVALUATION

        # Evaluate deterministic rule patterns
        for intent, pattern in cls.INTENT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return intent

        return ChatIntent.GENERAL_CHAT
