import asyncio

from q_haderslev_vbo.playwright.browser_session import BrowserSession


async def main():
    # -------------------------------------------------
    # Start BrowserSession
    # -------------------------------------------------
    session = BrowserSession(headless=True,debug=True)  # debug slået til    )
    await session.start()
    page = await session.new_page()
    
    try:
        # -------------------------------------------------
        # ÉN primær page
        # -------------------------------------------------

        try:
            await page.click("#findes-ikke")
        except Exception:
            await session.recorder.screenshot(
                page=page,
                session=session,
                name="exception_opstod",
                always=True
            )

    finally:
        # -------------------------------------------------
        # Luk ALT
        # -------------------------------------------------
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())