import asyncio
from playwright.async_api import async_playwright

from q_cura.launch import launch_cura
from q_haderslev_vbo.playwright.browser_session import BrowserSession


async def main():
    # -------------------------------------------------
    # 1. Opret browser-session (run-sandhed)
    # -------------------------------------------------
    session = BrowserSession(headless=False, debug=True, video=True)
    await session.start()
    page = await session.new_page()

    try:

        # -------------------------------------------------
        # 4. Kør launch_cura (login-flow)
        # -------------------------------------------------
        await launch_cura(
            page=page,
            session=session
        )

        print("✅ Cura klar:", page.url)

        # -------------------------------------------------
        # 5. Tag print-screen (HER oprettes mappen)
        # -------------------------------------------------
        await session.screenshot(
            page=page,
            name="STEP_1_cura_efter_login"
        )

        print("✅ Screenshot gemt")

    finally:
        # -------------------------------------------------
        # 6. Luk browser-session pænt
        # -------------------------------------------------
        await session.close()


# -------------------------------------------------
# Kør programmet
# -------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())