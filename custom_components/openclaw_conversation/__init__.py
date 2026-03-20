"""OpenClaw Conversation integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.components.conversation import async_set_agent, async_unset_agent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .conversation import OpenClawConversationAgent
from .config_flow import OpenClawConversationOptionsFlow

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up OpenClaw Conversation."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpenClaw Conversation from a config entry."""
    hass.config_entries.async_setup_platforms(entry, [])
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    agent = OpenClawConversationAgent(hass, entry)
    async_set_agent(hass, entry, agent)
    _LOGGER.info("OpenClaw Conversation agent registered")
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload OpenClaw Conversation."""
    async_unset_agent(hass, entry)
    return True
