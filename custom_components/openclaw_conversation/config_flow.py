"""Config flow for OpenClaw Conversation."""

from __future__ import annotations

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME

from .const import (
    CONF_AGENT_ID,
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_MODEL,
    CONF_TIMEOUT,
    DEFAULT_AGENT_ID,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)


class OpenClawConversationConfigFlow(
    config_entries.ConfigFlow, domain=DOMAIN
):
    """Handle a config flow for OpenClaw Conversation."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OpenClawConversationOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            base_url = user_input[CONF_BASE_URL].rstrip("/")
            api_key = user_input[CONF_API_KEY]
            agent_id = user_input.get(CONF_AGENT_ID, DEFAULT_AGENT_ID)

            # Test connection
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "x-openclaw-agent": agent_id,
                    }
                    payload = {
                        "model": user_input.get(CONF_MODEL, DEFAULT_MODEL),
                        "agentId": agent_id,
                        "messages": [
                            {"role": "user", "content": "ping"}
                        ],
                    }
                    async with session.post(
                        f"{base_url}/v1/chat/completions?agentId={agent_id}",
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as resp:
                        if resp.status == 401:
                            errors["base"] = "invalid_auth"
                        elif resp.status == 405:
                            errors["base"] = "endpoint_disabled"
                        elif resp.status not in (200,):
                            errors["base"] = "cannot_connect"
            except (aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"

            if not errors:
                name = user_input.get(CONF_NAME, "OpenClaw")
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_BASE_URL: base_url,
                        CONF_API_KEY: api_key,
                        CONF_MODEL: user_input.get(
                            CONF_MODEL, DEFAULT_MODEL
                        ),
                        CONF_TIMEOUT: user_input.get(
                            CONF_TIMEOUT, DEFAULT_TIMEOUT
                        ),
                        CONF_AGENT_ID: agent_id,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_NAME, default="OpenClaw"
                    ): str,
                    vol.Required(
                        CONF_BASE_URL, default=DEFAULT_BASE_URL
                    ): str,
                    vol.Required(CONF_API_KEY): str,
                    vol.Optional(
                        CONF_MODEL, default=DEFAULT_MODEL
                    ): str,
                    vol.Optional(
                        CONF_TIMEOUT, default=DEFAULT_TIMEOUT
                    ): vol.Coerce(int),
                    vol.Optional(
                        CONF_AGENT_ID, default=DEFAULT_AGENT_ID
                    ): str,
                }
            ),
            errors=errors,
        )


class OpenClawConversationOptionsFlow(config_entries.OptionsFlow):
    """Handle OpenClaw Conversation options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_agent_id = self.config_entry.options.get(
            CONF_AGENT_ID,
            self.config_entry.data.get(CONF_AGENT_ID, DEFAULT_AGENT_ID),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_AGENT_ID,
                        default=current_agent_id,
                    ): str,
                }
            ),
        )
