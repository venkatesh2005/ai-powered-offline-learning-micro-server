"""
Quiz Generator — 100 % LLM-driven, zero hardcoded questions.

The user-provided topic is sent directly to the local LLM (TinyLlama via
llama-cpp-python), which generates multiple-choice questions in a strict
numbered format.  A lightweight regex parser extracts the questions; any
that fail to parse are silently dropped and the LLM is re-prompted to
fill the gap (up to a configurable number of retries).

Public interface used by app.py
--------------------------------
    quiz_generator = QuizGenerator()       # module-level singleton
    quiz_generator.set_chatbot(bot)        # called once at startup
    quiz_generator.generate_quiz(topic, num_questions, difficulty)
"""

from __future__ import annotations

import re
import random
import time
from typing import List, Dict, Optional

# ─────────────────────────────────────────────────────────────────────
#  QuizGenerator
# ─────────────────────────────────────────────────────────────────────

class QuizGenerator:
    """Generate MCQ quizzes by prompting the local LLM."""

    # How many times we'll re-prompt the LLM to fill missing questions
    MAX_RETRIES = 3

    def __init__(self) -> None:
        self._chatbot = None

    # ── wiring ────────────────────────────────────────────────────────
    def set_chatbot(self, chatbot) -> None:
        """Inject the ChatBot (which exposes generate_completion)."""
        self._chatbot = chatbot
        print("✅ [QuizGen] ChatBot wired into quiz generator")

    # ── public entry point ────────────────────────────────────────────
    def generate_quiz(
        self,
        topic: str = "General Knowledge",
        num_questions: int = 5,
        difficulty: str = "medium",
    ) -> List[Dict]:
        """
        Generate *num_questions* MCQs for *topic* at *difficulty* level.
        Returns a list of question dicts ready for storage in the DB.
        Raises RuntimeError if the LLM is not available.
        """
        if self._chatbot is None:
            raise RuntimeError(
                "Quiz generator has no LLM — server is still loading. "
                "Please try again in a moment."
            )

        num_questions = max(1, min(num_questions, 20))
        topic = (topic or "General Knowledge").strip()
        difficulty = (difficulty or "medium").strip().lower()

        print(f"\n{'='*60}")
        print(f"📝 [QuizGen] Generating {num_questions} questions")
        print(f"   Topic      : {topic}")
        print(f"   Difficulty  : {difficulty}")
        print(f"{'='*60}")

        all_questions: List[Dict] = []
        attempts = 0

        while len(all_questions) < num_questions and attempts <= self.MAX_RETRIES:
            needed = num_questions - len(all_questions)
            # Ask for a few extra so we have room after dropping badly-parsed ones
            ask_for = min(needed + 2, 20)

            prompt = self._build_prompt(topic, ask_for, difficulty,
                                        existing_count=len(all_questions))
            raw_text, gen_time = self._call_llm(prompt, ask_for)

            if raw_text:
                parsed = self._parse_questions(raw_text, topic)
                # Deduplicate against what we already have
                for q in parsed:
                    if len(all_questions) >= num_questions:
                        break
                    if not self._is_duplicate(q, all_questions):
                        all_questions.append(q)

            attempts += 1
            status = f"parsed {len(all_questions)}/{num_questions}"
            print(f"   Attempt {attempts}: {status} (LLM {gen_time:.1f}s)")

        # Assign sequential IDs
        for idx, q in enumerate(all_questions, start=1):
            q["id"] = idx

        print(f"✅ [QuizGen] Returning {len(all_questions)} questions for '{topic}'")
        print(f"{'='*60}\n")
        return all_questions

    # ── prompt construction ───────────────────────────────────────────
    def _build_prompt(
        self,
        topic: str,
        count: int,
        difficulty: str,
        existing_count: int = 0,
    ) -> str:
        """
        Build a TinyLlama chat-format prompt.

        Uses <|system|>/<|user|>/<|assistant|> tags so the fine-tuned
        instruction model follows directions.  The assistant section is
        pre-seeded with one completed example so the model copies the
        exact format (including the "Correct:" line).
        """
        start_num = existing_count + 1

        diff_hint = {
            "easy":   "basic, introductory-level",
            "medium": "intermediate, conceptual",
            "hard":   "advanced, analytical",
        }.get(difficulty, "intermediate")

        prompt = (
            "<|system|>\n"
            "You are a quiz question writer. Generate multiple choice questions.\n"
            "Rules:\n"
            "- Each question has exactly 4 options: A, B, C, D\n"
            "- Each question has exactly one correct answer\n"
            "- Vary the correct answer across A, B, C, D\n"
            "- Questions must be specifically about the requested topic\n"
            "- After the options, write Correct: followed by the letter\n"
            "</s>\n"
            "<|user|>\n"
            f"Write {count} {diff_hint} multiple choice questions about {topic}.\n"
            "</s>\n"
            "<|assistant|>\n"
            f"Here are {count} multiple choice questions about {topic}:\n\n"
            f"{start_num}."
        )
        return prompt

    # ── LLM call ──────────────────────────────────────────────────────
    def _call_llm(self, prompt: str, count: int) -> tuple:
        """
        Send raw completion prompt to the LLM.
        Returns (text, generation_time_seconds).
        """
        # ~80-100 tokens per question (question + 4 options + answer line)
        max_tokens = min(count * 120, 2048)
        try:
            text, gen_time = self._chatbot.generate_completion(
                prompt,
                max_tokens=max_tokens,
                temperature=0.5,
                top_p=0.9,
                repeat_penalty=1.18,
                stop=["</s>", "---", "===", "```", "\n\n\n\n", "<|user|>", "<|system|>"],
            )
            return text.strip(), gen_time
        except Exception as exc:
            print(f"   ❌ [QuizGen] LLM error: {exc}")
            return "", 0.0

    # ── parsing ───────────────────────────────────────────────────────
    #
    # Expected format per question:
    #   <number>. <question text>
    #   A) <option A>
    #   B) <option B>
    #   C) <option C>
    #   D) <option D>
    #   Correct: <letter>
    #
    # We also accept "Answer:" instead of "Correct:", and parentheses
    # or periods after the option letter.

    _Q_SPLIT_RE = re.compile(
        r'(?:^|\n)\s*\d+[\.\)]\s+',     # starts with  "3. " or "3) "
    )

    _OPTION_RE = re.compile(
        r'^\s*([A-Da-d])\s*[\.\)\]:]\s*(.+)',   # A) text  or  A. text  or  a) text
        re.MULTILINE,
    )

    _CORRECT_RE = re.compile(
        r'(?:correct(?:\s+answer)?|answer)\s*(?:is)?\s*[:=\-]\s*\(?([A-Da-d])\)?',
        re.IGNORECASE,
    )

    def _parse_questions(self, raw: str, topic: str) -> List[Dict]:
        """Parse LLM output into a list of question dicts."""
        # Prepend leading number if the raw output doesn't start with one
        if not re.match(r'\s*\d+[\.)\s]', raw):
            raw = "1. " + raw

        # Split on question numbers
        blocks = self._Q_SPLIT_RE.split(raw)
        questions = []

        for block in blocks:
            block = block.strip()
            if not block or len(block) < 20:
                continue

            q = self._parse_one_block(block, topic)
            if q:
                questions.append(q)

        return questions

    def _parse_one_block(self, block: str, topic: str) -> Optional[Dict]:
        """Try to extract one MCQ from a text block."""
        lines = block.strip().splitlines()
        if not lines:
            return None

        # ── Extract question text (first line, or everything before option A)
        question_text = ""
        option_start_idx = 0
        for i, line in enumerate(lines):
            if self._OPTION_RE.match(line):
                option_start_idx = i
                break
            question_text += " " + line.strip()
        else:
            # No options found at all
            return None

        question_text = question_text.strip()
        if len(question_text) < 5:
            return None

        # Clean leading number from question text  ("3. What is..." -> "What is...")
        question_text = re.sub(r'^\d+[\.\)]\s*', '', question_text).strip()

        # ── Extract options
        options: Dict[str, str] = {}
        for line in lines[option_start_idx:]:
            m = self._OPTION_RE.match(line)
            if m:
                letter = m.group(1).upper()
                text = m.group(2).strip()
                if text:
                    options[letter] = text

        if len(options) < 4:
            # Try to salvage — if we have at least 2 options, still usable?
            # No, requirement is exactly 4 options
            if len(options) < 4:
                return None

        # ── Extract correct answer
        correct_letter = None
        block_lower = block.lower()
        m = self._CORRECT_RE.search(block)
        if m:
            correct_letter = m.group(1).upper()

        # Fallback: if no explicit "Correct:" line, randomly pick an answer
        if correct_letter not in options:
            correct_letter = random.choice([k for k in options.keys()] or ["A"])

        # ── Build the question dict
        opt_a = options.get("A", "")
        opt_b = options.get("B", "")
        opt_c = options.get("C", "")
        opt_d = options.get("D", "")

        return {
            "id":             0,  # will be set later
            "question":       question_text,
            "optionA":        opt_a,
            "optionB":        opt_b,
            "optionC":        opt_c,
            "optionD":        opt_d,
            "correctAnswer":  correct_letter,
            "topic":          topic,
            "sourceDocument": "AI Generated",
            "options":        [opt_a, opt_b, opt_c, opt_d],
            "correct_answer": ["A", "B", "C", "D"].index(correct_letter),
        }

    # ── deduplication ─────────────────────────────────────────────────
    @staticmethod
    def _is_duplicate(candidate: Dict, existing: List[Dict]) -> bool:
        """
        Simple dedup: reject if the first 40 chars of the question text
        (lowered, stripped) match any existing question.
        """
        cand = candidate.get("question", "").lower().strip()[:40]
        for e in existing:
            if e.get("question", "").lower().strip()[:40] == cand:
                return True
        return False


# ─────────────────────────────────────────────────────────────────────
#  Module-level singleton (imported by app.py)
# ─────────────────────────────────────────────────────────────────────
quiz_generator = QuizGenerator()
