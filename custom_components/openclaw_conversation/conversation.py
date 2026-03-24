"""Conversation agent for OpenClaw."""

from __future__ import annotations

import logging
import time
from typing import Literal

import aiohttp

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.util import ulid

from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_AGENT_ID,
    CONF_INACTIVITY_RESET_MINUTES,
    CONF_MODEL,
    CONF_PERSISTENT_CONVERSATION_ID,
    CONF_RISKY_CONFIRMATION_ENABLED,
    CONF_TIMEOUT,
    DEFAULT_AGENT_ID,
    DEFAULT_INACTIVITY_RESET_MINUTES,
    DEFAULT_MAX_CONVERSATION_MESSAGES,
    DEFAULT_MODEL,
    DEFAULT_RISKY_CONFIRMATION_ENABLED,
    DEFAULT_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)
RISKY_KEYWORDS = (
    "unlock",
    "disarm",
    "open garage",
    "garage door",
    "front door",
    "door lock",
    "security system",
)
CONFIRM_KEYWORDS = {"confirm", "yes confirm"}
CANCEL_KEYWORDS = {"cancel", "no"}


class OpenClawConversationAgent(conversation.AbstractConversationAgent):
    """OpenClaw conversation agent."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry
        self._base_url = entry.data[CONF_BASE_URL]
        self._api_key = entry.data[CONF_API_KEY]
        self._model = entry.data.get(CONF_MODEL, DEFAULT_MODEL)
        self._timeout = entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
        self._agent_id = (
            entry.options.get(
                CONF_AGENT_ID,
                entry.data.get(CONF_AGENT_ID, DEFAULT_AGENT_ID),
            ).strip()
            or DEFAULT_AGENT_ID
        )
        self._conversations: dict[str, list[dict]] = {}
        self._pending_risky_requests: dict[str, str] = {}
        self._last_activity: dict[str, float] = {}

    @property
    def attribution(self) -> dict[str, str]:
        """Return attribution."""
        return {"name": "Powered by OpenClaw", "url": "https://openclaw.ai"}

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return supported languages."""
        return "*"

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a sentence."""
        # Use persistent conversation ID if configured, otherwise use HA's ID
        persistent_id = self.entry.options.get(CONF_PERSISTENT_CONVERSATION_ID, "").strip() or self.entry.data.get(CONF_PERSISTENT_CONVERSATION_ID, "").strip()
        conversation_id = persistent_id or user_input.conversation_id or ulid.ulid_now()

        # Apply inactivity guardrail
        now = time.monotonic()
        inactivity_minutes = self._get_int_option(
            CONF_INACTIVITY_RESET_MINUTES,
            DEFAULT_INACTIVITY_RESET_MINUTES,
        )
        if inactivity_minutes < 0:
            inactivity_minutes = 0
        last_activity = self._last_activity.get(conversation_id)
        if inactivity_minutes and last_activity is not None:
            if now - last_activity > inactivity_minutes * 60:
                self._conversations.pop(conversation_id, None)
                self._pending_risky_requests.pop(conversation_id, None)
        self._last_activity[conversation_id] = now

        messages = list(self._conversations.get(conversation_id, []))

        user_text = (user_input.text or "").strip()
        user_text_to_process = user_text
        normalized_input = user_text.lower()
        pending_request = self._pending_risky_requests.get(conversation_id)
        skip_risky_check = False

        if pending_request:
            if normalized_input in CONFIRM_KEYWORDS:
                user_text_to_process = pending_request
                skip_risky_check = True
                self._pending_risky_requests.pop(conversation_id, None)
            elif normalized_input in CANCEL_KEYWORDS:
                self._pending_risky_requests.pop(conversation_id, None)
                return self._build_response(
                    "Canceled.", user_input.language, conversation_id
                )
            else:
                self._pending_risky_requests.pop(conversation_id, None)
        
        risky_confirmation_enabled = bool(
            self.entry.options.get(
                CONF_RISKY_CONFIRMATION_ENABLED,
                DEFAULT_RISKY_CONFIRMATION_ENABLED,
            )
        )

        if (
            risky_confirmation_enabled
            and not skip_risky_check
            and self._contains_risky_keyword(user_text_to_process)
        ):
            self._pending_risky_requests[conversation_id] = user_text_to_process
            prompt = (
                f"Please confirm: {user_text_to_process}. Say 'confirm' to proceed or 'cancel'."
            )
            return self._build_response(
                prompt, user_input.language, conversation_id
            )

        if not user_text_to_process:
            user_text_to_process = user_text

        messages.append({"role": "user", "content": user_text_to_process})

        try:
            response_text = await self._call_openclaw(messages, conversation_id)
        except Exception as err:
            _LOGGER.error("Error calling OpenClaw: %s", err)
            response_text = "Erreur de communication avec OpenClaw."

        messages.append({"role": "assistant", "content": response_text})

        max_messages = max(
            1,
            self._get_int_option(
                "max_conversation_messages", DEFAULT_MAX_CONVERSATION_MESSAGES
            ),
        )
        self._conversations[conversation_id] = messages[-max_messages:]

        return self._build_response(
            response_text, user_input.language, conversation_id
        )

    async def _call_openclaw(self, messages: list[dict], conversation_id: str) -> str:
        """Call OpenClaw chat completions API."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        session_user = f"{self._agent_id}:{conversation_id}"
        payload = {
            "model": self._model,
            "messages": messages,
            "user": session_user,
            "agentId": self._agent_id,
        }

        timeout_sec = int(self.entry.options.get(CONF_TIMEOUT, self._timeout))
        timeout = aiohttp.ClientTimeout(total=timeout_sec)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(
                        f"OpenClaw returned {resp.status}: {body[:200]}"
                    )

                data = await resp.json()
                choices = data.get("choices", [])
                if not choices:
                    raise RuntimeError("No response from OpenClaw")

                return choices[0]["message"]["content"]

    def _build_response(
        self, text: str, language: str, conversation_id: str
    ) -> conversation.ConversationResult:
        """Build a conversation result."""
        response = intent.IntentResponse(language=language)
        response.async_set_speech(text)
        return conversation.ConversationResult(
            response=response, conversation_id=conversation_id
        )

    def _contains_risky_keyword(self, text: str) -> bool:
        """Return True if the text contains a risky keyword."""
        normalized = (text or "").lower()
        return any(keyword in normalized for keyword in RISKY_KEYWORDS)

    def _get_int_option(self, key: str, default: int) -> int:
        """Return an int option, falling back to default on error."""
        value = self.entry.options.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
