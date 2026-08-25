import asyncio

from playwright.async_api import async_playwright

RIFTBOUND_SETS=["Origins", "Spiritforged", "Unleashed", "Vendetta"]

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

        search_info = 0

        flag = True
        count = 0
        while(flag):
            search_item = page.locator(".search-result__content").nth(count)
            await search_item.wait_for(
                state="visible",
                timeout=20_000,
            )
            search_info = await search_item.inner_text()
            if (search_info[:search_info.find('\n')] in RIFTBOUND_SETS):
                flag = False
            count += 1
            


        await browser.close()

        # return (price[price.find(":") + 1:])
        return search_info

async def main():
    result = await search_website(
        "time warp"
    )

    print(result)

asyncio.run(main())