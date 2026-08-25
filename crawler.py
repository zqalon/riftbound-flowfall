import asyncio

from playwright.async_api import async_playwright

async def search_website(search: str):
    url = "tcgplayer.com"

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

        await page.wait_for_load_state("domcontentloaded")

        text = await page.locator(".product-card__market-price--value").first.inner_text()

        await browser.close()

        return text

async def main():
    result = await search_website(
        "Time Warp"
    )

    print(result)

asyncio.run(main())