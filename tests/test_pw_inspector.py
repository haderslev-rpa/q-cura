import asyncio

from q_haderslev_vbo.playwright.browser_session import BrowserSession
from q_cura.functionality.launch import launch_cura


async def main():
    # Browseren skal være synlig for Inspector.
    session = BrowserSession(
        headless=False,
        debug=True,
        video=False,
    )

    await session.start()
    page = await session.new_page()

    try:
        # Åbn Cura og log ind.
        await launch_cura(
            page=page,
            session=session,
        )

        print("Cura er åbnet.")
        print("Playwright stopper nu ved page.pause().")

        # Her skal Playwright Inspector åbne.
        await page.pause()

        # Denne linje køres, når du trykker Resume i Inspector.
        print("Koden fortsætter efter pausen.")

        # Endnu en pause, så browseren ikke lukkes med det samme.
        await page.pause()

    finally:
        await session.close()
        print("Browser-session lukket korrekt.")


if __name__ == "__main__":
    asyncio.run(main())