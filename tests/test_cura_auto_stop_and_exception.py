import asyncio

from q_haderslev_vbo.playwright.browser_session import BrowserSession
from q_cura.launch import launch_cura
from q_cura.liste_forebyggende_hjaemmebesoeg import (liste_forebyggende_hjaemmebesoeg
)


async def main():
    # -------------------------------------------------
    # 1. Start BrowserSession
    # -------------------------------------------------
    session = BrowserSession(
        headless=True,
        debug=False  # debug styres her
    )
    await session.start()
    page = await session.new_page()

    try:

        # -------------------------------------------------
        # DEL A – NORMAL FLOW
        # -------------------------------------------------
        await launch_cura(page=page, session=session)

        await liste_forebyggende_hjaemmebesoeg(
            page=page,
            session=session,
            alder=75,
            maaned="Maj"
        )

        await asyncio.sleep(5)

        # -------------------------------------------------
        # DEL B – EXCEPTION
        # -------------------------------------------------
        try:
            await page.click("#findes-ikke")
        except Exception:
            await session.recorder.screenshot(
                page=page,
                session=session,
                name="STEP_exception_opstod",
                always=True
            )

    finally:
        # -------------------------------------------------
        # Luk ALT korrekt
        # -------------------------------------------------
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())