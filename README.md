# Chat history recovery and sidebar fix

## Replace these files

1. `Chat.jsx` -> `src/pages/Chat.jsx`
2. `chat_routes_updated.py` -> replace the existing backend chat routes module (the file that defines `router = APIRouter(prefix="/api/chat", ...)`). Keep its existing import path and router registration.
3. `apiClient_history_fix.js` -> `src/api/apiClient.js` only if the current file does not already contain `getConversations`, `getConversation`, `saveConversation`, and `deleteConversation` methods.

## What this fixes

- Migrates old `chat_messages` documents that have no `conversationId` into stable conversation IDs.
- Uses a 60-minute inactivity gap to split timestamped legacy messages into separate chat sessions.
- Preserves existing `conversation_id` snake_case values.
- Rebuilds missing `chat_conversations` summary rows from saved message documents.
- Makes old messages loadable by the individual conversation endpoint.
- Deletes messages, summary rows, and artifacts for only the selected conversation.
- Makes the delete control visible in the sidebar and refreshes the sidebar after deletion.

## Important limitation

Older messages with no conversation ID and no usable timestamp cannot be reliably separated into their original chat sessions. They are preserved together in one legacy conversation rather than discarded. If the old backend already permanently deleted message documents, this code cannot recreate their text. Do not clear MongoDB collections while testing.

## Before installing

Take a MongoDB Atlas backup/export of `chat_messages`, `chat_conversations`, and `chat_artifacts`.

## After installing

Restart the backend and frontend. Open AI Copilot Chat and allow the conversation list to load. The first call to `GET /api/chat/conversations` performs a one-time in-place migration of legacy messages for the authenticated user. Then test opening and deleting one conversation, refreshing, and checking that other conversations remain.

Backend syntax was checked with `python -m py_compile`. The complete application build and live MongoDB migration were not run in this environment.
