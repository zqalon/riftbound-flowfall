# Riftbound Discord Card Bot

A small Discord bot that watches normal user messages for Riftbound card names in square brackets and replies with a Discord embed containing the card's details and rules text.

Examples:

- `[Acceptable Losses]`
- `What does [Jinx, Loose Cannon] do?`
- `Compare [Card A] with [Card B]`

The bot uses the public Riftcodex API. Riftcodex currently documents exact and fuzzy name lookup at `/cards/name`; no API authentication is required for read operations.

## 1. Create the Discord application

Create a bot application in the Discord Developer Portal, add a bot user, and copy its token.

Enable **Message Content Intent** on the bot's settings. The bot needs this because it reads ordinary user message text.

When inviting it, give it the minimum permissions it needs:

- View Channels
- Send Messages
- Embed Links
- Read Message History

## 2. Run locally

Use Python 3.10+.

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
playwright install
```

Set `DISCORD_TOKEN` in `.env` and export it before starting the bot:

```bash
export DISCORD_TOKEN="your-token-here"
python bot.py
```

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
$env:DISCORD_TOKEN="your-token-here"
python bot.py
```

The included bot deliberately does not load `.env` automatically, so there is no extra dotenv dependency. You can use a process manager, Docker, or your hosting provider's secret/environment-variable system instead.

## 3. How matching works

The bot looks for text matching:

```text
[card name]
```

It first calls:

```text
GET https://api.riftcodex.com/cards/name?exact=<card name>
```

If that returns no match, it tries:

```text
GET https://api.riftcodex.com/cards/name?fuzzy=<card name>
```

Riftcodex returns card fields including name, Riftbound ID, collector number, attributes, classification, rules text, set, and media. The bot turns those into a Discord embed.

A five-minute in-memory cache is enabled by default to avoid repeatedly requesting the same card.

## Notes

- The bot ignores messages authored by bots, preventing reply loops.
- Up to 10 bracketed card names are processed per message because Discord limits a message to 10 embeds.
- If a card is not found, the bot reports the unmatched bracketed name.
- The Riftcodex API is an unofficial fan project and is not affiliated with Riot Games.
