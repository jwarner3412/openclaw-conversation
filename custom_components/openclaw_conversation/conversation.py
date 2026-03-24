"""Conversation agent for OpenClaw."""

from __future__ import annotations

import logging
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import aiohttp

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.util import ulid

from .const import (
    CONF_AGENT_ID,
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_MODEL,
    CONF_TIMEOUT,
    DEFAULT_AGENT_ID,
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class OpenClawConversationAgent(conversation.AbstractConversationAgent):
    """OpenClaw conversation agent."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry
        self._base_url = entry.data[CONF_BASE_URL]
        self._api_key = entry.data[CONF_API_KEY]
        self._model = entry.options.get(
            CONF_MODEL,
            entry.data.get(CONF_MODEL, DEFAULT_MODEL),
        )
        self._timeout = entry.options.get(
            CONF_TIMEOUT,
            entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
        )
        self._agent_id = entry.options.get(
            CONF_AGENT_ID,
            entry.data.get(CONF_AGENT_ID, DEFAULT_AGENT_ID),
        )
        self._conversations: dict[str, list[dict]] = {}

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
        conversation_id = user_input.conversation_id or ulid.ulid_now()

        # Get or create conversation history
        messages = self._conversations.get(conversation_id, [])

        # Add user message
        messages.append({"role": "user", "content": user_input.text})

        # Call OpenClaw
        try:
            response_text = await self._call_openclaw(messages, conversation_id)
        except Exception as err:
            _LOGGER.error("Error calling OpenClaw: %s", err)
            response_text = "Erreur de communication avec OpenClaw."

        # Add assistant response to history
        messages.append({"role": "assistant", "content": response_text})

        # Keep conversation history (limit to last 20 messages)
        self._conversations[conversation_id] = messages[-20:]

        # Build response
        response = intent.IntentResponse(language=user_input.language)
        response.async_set_speech(response_text)

        return conversation.ConversationResult(
            response=response,
            conversation_id=conversation_id,
        )

    async def _call_openclaw(
        self, messages: list[dict], conversation_id: str
    ) -> str:
        """Call OpenClaw chat completions API."""
        session_user = f"{self._agent_id}:{conversation_id}"
        endpoint = self._build_endpoint_with_agent_id(
            f"{self._base_url}/v1/chat/completions"
        )

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "x-openclaw-agent": self._agent_id,
        }

        payload = {
            "model": self._model,
            "messages": messages,
            "user": session_user,
            "agentId": self._agent_id,
        }

        timeout = aiohttp.ClientTimeout(total=self._timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                endpoint,
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

    def _build_endpoint_with_agent_id(self, endpoint: str) -> str:
        """Append agentId to endpoint query string."""
        parts = urlsplit(endpoint)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query["agentId"] = self._agent_id
        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                urlencode(query),
                parts.fragment,
            )
        )
