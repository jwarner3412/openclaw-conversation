"""Constants for OpenClaw Conversation."""

DOMAIN = "openclaw_conversation"

CONF_BASE_URL = "base_url"
CONF_API_KEY = "api_key"
CONF_MODEL = "model"
CONF_TIMEOUT = "timeout"
CONF_PERSISTENT_CONVERSATION_ID = "persistent_conversation_id"
CONF_AGENT_ID = "agent_id"
CONF_INACTIVITY_RESET_MINUTES = "inactivity_reset_minutes"
CONF_RISKY_CONFIRMATION_ENABLED = "risky_confirmation_enabled"

DEFAULT_MODEL = "openclaw"
DEFAULT_AGENT_ID = "main"
DEFAULT_TIMEOUT = 30
DEFAULT_BASE_URL = "http://127.0.0.1:18789"
DEFAULT_INACTIVITY_RESET_MINUTES = 30
DEFAULT_RISKY_CONFIRMATION_ENABLED = True
DEFAULT_MAX_CONVERSATION_MESSAGES = 50
