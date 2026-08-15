import os
import re
import time
import asyncio
from typing import Any

import aiohttp
import discord
from discord.ext import commands


RIFTCODEX_BASE_URL = "https://api.riftcodex.com"
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
MAX_CARD_LOOKUPS_PER_MESSAGE = 10
BRACKET_PATTERN = re.compile(r"\[([^\[\]\n]{1,100})\]")


def extract_items(payload: Any) -> list[dict]:
    """Accept the common Riftcodex response shapes: a list or {items: [...]}."""
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            return [x for x in items if isinstance(x, dict)]
        # A single card object can also be returned by an endpoint.
        if payload.get("name"):
            return [payload]
    return []


class RiftcodexClient:
    def __init__(self) -> None:
        self.session: aiohttp.ClientSession | None = None
        self.cache: dict[str, tuple[float, dict | None]] = {}

    async def start(self) -> None:
        timeout = aiohttp.ClientTimeout(total=10)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={"User-Agent": "RiftboundDiscordBot/1.0"},
        )

    async def close(self) -> None:
        if self.session:
            await self.session.close()

    async def _get_json(self, path: str, params: dict[str, str]) -> Any:
        if not self.session:
            raise RuntimeError("Riftcodex client is not started")

        async with self.session.get(
            f"{RIFTCODEX_BASE_URL}{path}",
            params=params,
        ) as response:
            if response.status == 404:
                return None
            response.raise_for_status()
            return await response.json()

    async def find_card(self, name: str) -> dict | None:
        key = name.strip().casefold()
        now = time.monotonic()

        cached = self.cache.get(key)
        if cached and now - cached[0] < CACHE_TTL_SECONDS:
            return cached[1]

        # Prefer exact matching so "[Jinx, Loose Cannon]" doesn't accidentally
        # resolve to a different similarly named card.
        payload = await self._get_json("/cards/name", {"exact": name.strip()})
        matches = extract_items(payload)

        if not matches:
            # Fall back to fuzzy matching for convenient bracket syntax.
            payload = await self._get_json("/cards/name", {"fuzzy": name.strip()})
            matches = extract_items(payload)

        card = matches[0] if matches else None
        self.cache[key] = (now, card)
        return card


def truncate(text: str, limit: int) -> str:
    text = text or ""
    return text if len(text) <= limit else text[: limit - 1] + "…"


def card_embed(card: dict) -> discord.Embed:
    attrs = card.get("attributes") or {}
    classification = card.get("classification") or {}
    text = card.get("text") or {}
    card_set = card.get("set") or {}
    media = card.get("media") or {}

    domains = classification.get("domain") or []
    if isinstance(domains, str):
        domains = [domains]

    stats = []
    if attrs.get("energy") is not None:
        stats.append(f"**Energy:** {attrs['energy']}")
    if attrs.get("might") is not None:
        stats.append(f"**Might:** {attrs['might']}")
    if attrs.get("power") is not None:
        stats.append(f"**Power:** {attrs['power']}")

    type_parts = [
        classification.get("supertype"),
        classification.get("type"),
    ]
    type_label = " ".join(x for x in type_parts if x)

    embed = discord.Embed(
        title=card.get("name", "Unknown card"),
        description=truncate(text.get("plain") or "No card text available.", 4096),
        url=(
            f"https://riftcodex.com/search?q="
            f"{card.get('name', '').replace(' ', '+')}"
        ),
    )

    # if type_label:
    #     embed.add_field(name="Type", value=truncate(type_label, 1024), inline=True)
    # if classification.get("rarity"):
    #     embed.add_field(
    #         name="Rarity",
    #         value=truncate(str(classification["rarity"]), 1024),
    #         inline=True,
    #     )
    # if domains:
    #     embed.add_field(
    #         name="Domain",
    #         value=truncate(", ".join(map(str, domains)), 1024),
    #         inline=True,
    #     )
    # if stats:
    #     embed.add_field(name="Stats", value="\n".join(stats), inline=True)

    # set_label = card_set.get("label") or card_set.get("set_id")
    # riftbound_id = card.get("riftbound_id")
    # collector = card.get("collector_number")

    # identifiers = []
    # if set_label:
    #     identifiers.append(f"**Set:** {set_label}")
    # if riftbound_id:
    #     identifiers.append(f"**ID:** `{riftbound_id}`")
    # if collector is not None:
    #     identifiers.append(f"**Collector #:** {collector}")

    # if identifiers:
    #     embed.add_field(name="Details", value="\n".join(identifiers), inline=False)

    # flavour = text.get("flavour")
    # if flavour:
    #     embed.add_field(name="Flavour", value=truncate(flavour, 1024), inline=False)

    image_url = media.get("image_url")
    if image_url:
        embed.set_thumbnail(url=image_url)

    # artist = media.get("artist")
    # if artist:
    #     embed.set_footer(text=f"Artist: {artist}")

    return embed


class RiftboundBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )
        self.riftcodex = RiftcodexClient()

    async def setup_hook(self) -> None:
        await self.riftcodex.start()

    async def close(self) -> None:
        await self.riftcodex.close()
        await super().close()


bot = RiftboundBot()


@bot.event
async def on_ready() -> None:
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return

    # Matches messages such as:
    #   [Jinx, Loose Cannon]
    #   Can someone explain [Acceptable Losses]?
    card_names = BRACKET_PATTERN.findall(message.content)
    if not card_names:
        return

    # De-duplicate while preserving order.
    unique_names = list(dict.fromkeys(name.strip() for name in card_names))
    unique_names = [name for name in unique_names if name][:MAX_CARD_LOOKUPS_PER_MESSAGE]

    embeds: list[discord.Embed] = []
    not_found: list[str] = []

    for name in unique_names:
        try:
            card = await bot.riftcodex.find_card(name)
        except aiohttp.ClientError:
            await message.reply(
                "I couldn't reach Riftcodex right now. Please try again in a moment.",
                mention_author=False,
            )
            return
        except asyncio.TimeoutError:
            await message.reply(
                "Riftcodex took too long to respond. Please try again in a moment.",
                mention_author=False,
            )
            return

        if card:
            embeds.append(card_embed(card))
        else:
            not_found.append(name)

    if not embeds and not_found:
        await message.reply(
            "I couldn't find " + ", ".join(f"`[{name}]`" for name in not_found) +
            " in Riftcodex.",
            mention_author=False,
        )
        return

    # Discord allows at most 10 embeds in one message.
    content = None
    if not_found:
        content = (
            "Not found: " +
            ", ".join(f"`[{name}]`" for name in not_found)
        )

    await message.reply(
        content=content,
        embeds=embeds[:10],
        mention_author=False,
    )


@bot.command()
async def ping(ctx: commands.Context) -> None:
    """Simple health check."""
    await ctx.send("Pong!")


def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError(
            "DISCORD_TOKEN is not set. Put your bot token in the environment."
        )
    bot.run(token)


if __name__ == "__main__":
    main()
