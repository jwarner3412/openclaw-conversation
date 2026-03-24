"""Config flow for OpenClaw Conversation."""

from __future__ import annotations

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME

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
    DEFAULT_BASE_URL,
    DEFAULT_INACTIVITY_RESET_MINUTES,
    DEFAULT_MAX_CONVERSATION_MESSAGES,
    DEFAULT_MODEL,
    DEFAULT_RISKY_CONFIRMATION_ENABLED,
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
        """Get the options flow handler."""
        return OpenClawConversationOptionsFlow()

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            base_url = user_input[CONF_BASE_URL].rstrip("/")
            api_key = user_input[CONF_API_KEY]

            # Test connection
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    }
                    payload = {
                        "model": user_input.get(CONF_MODEL, DEFAULT_MODEL),
                        "messages": [
                            {"role": "user", "content": "ping"}
                        ],
                    }
                    async with session.post(
                        f"{base_url}/v1/chat/completions",
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
                        CONF_AGENT_ID: user_input.get(
                            CONF_AGENT_ID, DEFAULT_AGENT_ID
                        ),
                        CONF_TIMEOUT: user_input.get(
                            CONF_TIMEOUT, DEFAULT_TIMEOUT
                        ),
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
                        CONF_AGENT_ID, default=DEFAULT_AGENT_ID
                    ): str,
                    vol.Optional(
                        CONF_TIMEOUT, default=DEFAULT_TIMEOUT
                    ): vol.Coerce(int),
                }
            ),
            errors=errors,
        )


class OpenClawConversationOptionsFlow(
    config_entries.OptionsFlow
):
    """Handle options for OpenClaw Conversation."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_PERSISTENT_CONVERSATION_ID,
                        default=self.config_entry.options.get(
                            CONF_PERSISTENT_CONVERSATION_ID, ""
                        ),
                    ): str,
                    vol.Optional(
                        "max_conversation_messages",
                        default=self.config_entry.options.get(
                            "max_conversation_messages",
                            DEFAULT_MAX_CONVERSATION_MESSAGES,
                        ),
                    ): vol.Coerce(int),
                    vol.Optional(
                        CONF_AGENT_ID,
                        default=self.config_entry.options.get(
                            CONF_AGENT_ID,
                            self.config_entry.data.get(
                                CONF_AGENT_ID, DEFAULT_AGENT_ID
                            ),
                        ),
                    ): str,
                    vol.Optional(
                        CONF_TIMEOUT,
                        default=self.config_entry.options.get(
                            CONF_TIMEOUT,
                            self.config_entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
                        ),
                    ): vol.Coerce(int),
                    vol.Optional(
                        CONF_INACTIVITY_RESET_MINUTES,
                        default=self.config_entry.options.get(
                            CONF_INACTIVITY_RESET_MINUTES,
                            DEFAULT_INACTIVITY_RESET_MINUTES,
                        ),
                    ): vol.Coerce(int),
                    vol.Optional(
                        CONF_RISKY_CONFIRMATION_ENABLED,
                        default=self.config_entry.options.get(
                            CONF_RISKY_CONFIRMATION_ENABLED,
                            DEFAULT_RISKY_CONFIRMATION_ENABLED,
                        ),
                    ): vol.Boolean(),
                }
            ),
        )
