import os
import re
import json
import logging
from django.conf import settings
from core.models import Product, Dealer, AssistantConversation
from .tools import AssistantToolRegistry
from .providers import (
    SYSTEM_PROMPT,
    MultiProviderOrchestrator,
    GeminiProvider,
    GroqProvider,
    DeterministicEngine,
    ProviderResult,
)

logger = logging.getLogger(__name__)


def extract_cited_skus(text: str, tool_skus: set) -> list[str]:
    """
    Finds every SKU mentioned in the reply or tools, and verifies that
    each cited SKU actually exists in the database.
    """
    candidates = set(tool_skus)
    # Search for standard SKU patterns (e.g. BRK-1044, OIL-1001, etc.)
    found_tokens = re.findall(r"\b[A-Z]{3}-\d{4}\b", text or "")
    candidates.update(found_tokens)

    # Validate against actual database
    valid_skus = set(
        Product.objects.filter(sku__in=candidates).values_list("sku", flat=True)
    )
    return sorted(list(valid_skus))


class AssistantEngine:
    def __init__(self, session_id: str, dealer_id: int):
        self.session_id = session_id
        self.dealer_id = dealer_id
        self.orchestrator = MultiProviderOrchestrator(session_id=session_id, dealer_id=dealer_id)
        self.tools = self.orchestrator.tools
        self.engine_used = "deterministic"
        self.api_key = getattr(settings, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = getattr(settings, "GEMINI_MODEL", "gemini-3.5-flash-lite")

    def run(self, message: str) -> dict:
        """Processes a chat turn with multi-provider failover orchestration."""
        # 1. Retrieve recent history for this session (isolated by session_id)
        recent_history = list(
            AssistantConversation.objects.filter(session_id=self.session_id)
            .order_by("-id")[:6]
        )
        recent_history.reverse()

        # 2. Run multi-provider failover turn
        turn_result = self.orchestrator.run_turn(message=message, history=recent_history)
        reply = turn_result.reply
        self.engine_used = turn_result.provider

        # 3. Extract valid cited SKUs verified against DB
        cited_skus = extract_cited_skus(reply, self.tools.cited_skus)

        # 4. Persist turn in session memory
        AssistantConversation.objects.create(
            session_id=self.session_id,
            dealer_id=self.dealer_id,
            role="user",
            content=message,
        )
        AssistantConversation.objects.create(
            session_id=self.session_id,
            dealer_id=self.dealer_id,
            role="assistant",
            content=reply,
            tool_calls=self.tools.recorded_tool_calls,
        )

        return {
            "reply": reply,
            "cited_skus": cited_skus,
            "tool_calls": self.tools.recorded_tool_calls,
            "actions": self.tools.recorded_actions,
            "engine": self.engine_used,
            "provider": self.engine_used,
        }

    def _run_gemini(self, message: str, history: list) -> str:
        """Backwards-compatible helper calling GeminiProvider directly."""
        res = self.orchestrator.gemini_provider.execute_turn(message, history, self.tools)
        if res.success:
            return res.reply
        raise RuntimeError(res.error_message or "Gemini execution failed")

    def _run_deterministic(self, message: str) -> str:
        """Backwards-compatible helper calling DeterministicEngine directly."""
        res = self.orchestrator.deterministic_engine.execute_turn(message, self.tools)
        return res.reply
