# OpenClaw Conversation (Fork)

Fork of [nicolasglg/openclaw-conversation](https://github.com/nicolasglg/openclaw-conversation) with persistent conversation ID support for voice sessions.

## What's Changed

### Persistent Conversation ID (new)
- Added **Options flow** with a "Persistent Conversation ID" field
- When set, all voice commands share the same conversation context
- This solves the issue where each voice command was a new session with zero memory of previous turns
- When empty/not set, falls back to default HA behavior (per-turn IDs)

### How to Use
1. Install via HACS (custom repository) or manually copy `custom_components/openclaw_conversation` to your HA `config/custom_components/`
2. Restart Home Assistant
3. Go to Settings → Devices → OpenClaw Conversation → **Configure** (or Options)
4. Set a Persistent Conversation ID (e.g., `ha-voice-james`)
5. All voice commands will now share conversation history (last 20 messages)

### Upstream
Based on [nicolasglg/openclaw-conversation](https://github.com/nicolasglg/openclaw-conversation) v0.1.0
