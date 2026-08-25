import asyncio

from playwright.async_api import async_playwright

async def search_website(search: str):
    url = "https://tcgplayer.com"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        await page.goto(
            url,
            wait_until="domcontentloaded",
        )

        search_box = page.locator(
            'input[name="acInput"]'
        )

        await search_box.fill(search)
        await search_box.press("Enter")

        result = page.locator(".search-result__content").nth(0)

        await result.wait_for(
            state="visible",
            timeout=20_000,
        )

        price = await result.text_content()

        await browser.close()

        return price[price.find(":") + 1:]

async def main():
    result = await search_website(
        "time warp"
    )

    print(result)

asyncio.run(main())