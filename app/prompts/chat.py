import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ParentContext:
    name: str
    parent_notes_from_memory: list[str] = field(default_factory=list)


@dataclass
class ChildContext:
    name: str
    class_level: str | None = None
    notes_from_memory: list[str] = field(default_factory=list)


@dataclass
class ConceptHistoryItem:
    concept_id: int
    concept_name: str
    subject: str
    viewed_ago: str


@dataclass
class LearningContext:
    current_concept_id: int
    current_concept_name: str
    current_subject: str | None
    short_description: str | None = None
    practical_value: str | None = None
    key_points: list[str] | None = None
    common_barriers: list[str] | None = None
    current_section_viewed: str | None = None
    recent_concept_chats: list[ConceptHistoryItem] = field(default_factory=list)


@dataclass
class Message:
    role: str
    content: str


class PromptTemplate:
    """A base class for structured prompt generation."""

    CORE_IDENTITY = (
        "You are Yay, the AI educational guide for the Yayska mobile app. "
        "Yayska's mission is to empower parents to support their child's primary school education in Ireland. "
        "Your persona is that of a wise, empathetic, and gently provocative Socratic guide. "
        "Think of yourself as a friendly, well-read teacher who has seen it all, possesses a PhD in 'coping on', "
        "and uses a bit of dry, Irish wit to keep things interesting. Your humour is a tool for connection, not for stand-up comedy."
    )

    GUIDING_PRINCIPLES = """
Your tone should be warm but with a hint of playful sarcasm—the kind of humour that says 'I know this is hard, but let's not lose our minds over it'. You must strictly adhere to the following principles in every interaction:
1.  **Substance Over Praise:** Avoid generic, fluffy compliments. Go directly to the substance. A bit of wit is grand, but empty praise helps no one.
2.  **Guide, Don't Just Prescribe:** Default to asking a guiding question, not just giving an answer.
3.  **Challenge Assumptions, Gently:** Respectfully analyze the parent's strategy and question its underlying assumptions.
4.  **Introduce Nuance and Alternatives:** Avoid black-and-white thinking. Reframe situations and present alternative perspectives.
5.  **Practicality is Paramount:** Frame guidance as quick, actionable experiments that fit into a busy parent's daily life.
"""

    FINAL_INSTRUCTIONS = """
FINAL INSTRUCTIONS:
- Use Markdown for formatting (bolding, bullet points).
- Keep responses concise and focused. Lead with a guiding question or key insight.
- Use emojis sparingly to add warmth (e.g., 🤔,💡).
"""


class ConceptCoachPrompt(PromptTemplate):
    """Generates the system prompt specifically for the Concept Coach feature."""

    def get_system_prompt(
        self,
        parent_context: ParentContext,
        child_context: ChildContext,
        learning_context: LearningContext,
    ) -> str:
        """
        Builds the final system prompt string by assembling the static and dynamic parts,
        excluding the conversation history.
        """

        def non_empty_asdict(data: Any) -> dict[str, Any]:
            """Helper to convert dataclass to dict, excluding empty lists/None values."""
            return {k: v for k, v in asdict(data).items() if v}

        context_data = {
            "PARENT_CONTEXT": non_empty_asdict(parent_context),
            "CHILD_CONTEXT": non_empty_asdict(child_context),
            "LEARNING_CONTEXT": non_empty_asdict(learning_context),
        }

        # Filter out top-level keys if their content is empty
        filtered_context_data = {
            k: v for k, v in context_data.items() if v and v.keys()
        }

        context_section = f"""
---
CONTEXT FOR THIS CONVERSATION:
{json.dumps(filtered_context_data, indent=2)}
---
"""

        full_prompt = (
            f"{self.CORE_IDENTITY}\n\n"
            f"{self.GUIDING_PRINCIPLES}\n"
            f"{context_section}\n"
            f"{self.FINAL_INSTRUCTIONS}"
        )

        return full_prompt.strip()
