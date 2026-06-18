import asyncio

from q_haderslev_vbo.playwright.browser_session import BrowserSession
from q_cura.functionality.launch import launch_cura
from q_cura.functionality.liste_forebyggende_hjaemmebesoeg import (liste_forebyggende_hjaemmebesoeg
)


async def main():
    # -------------------------------------------------
    # 1. Start BrowserSession
    # -------------------------------------------------
    session = BrowserSession(headless=True,debug=True)  # video + screenshots    
    await session.start()
    page = await session.new_page()

    try:
  

        # -------------------------------------------------
        # 3. Login i Cura
        # -------------------------------------------------
        await launch_cura(page=page, session=session)

        # -------------------------------------------------
        # 4. Kør Forebyggende hjemmebesøg
        # -------------------------------------------------
        
        await liste_forebyggende_hjaemmebesoeg(
            page=page,
            session=session,
            alder=75,
            maaned="Maj"
        )

        await asyncio.sleep(3)

    finally:
        # -------------------------------------------------
        # 5. Luk ALT
        # -------------------------------------------------
        await session.close()
        print("✅ Browser-session lukket korrekt")


if __name__ == "__main__":
    asyncio.run(main())