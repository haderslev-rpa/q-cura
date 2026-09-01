import asyncio
import os

from q_haderslev_vbo.playwright.browser_session import BrowserSession
from q_cura.functionality.launch import launch_cura
from q_cura.functionality.opret_borger import opret_borger


async def main():
    # Hent test-CPR fra miljøvariablen cpr1.
    cpr = os.getenv("cpr1")

    if not cpr:
        raise ValueError("cpr1 mangler i miljøvariablerne.")

    # Start browser-session.
    session = BrowserSession(
        headless=False,
        debug=False,
        video=False,
    )

    await session.start()
    page = await session.new_page()

    try:
        # Login i Cura.
        await launch_cura(
            page=page,
            session=session,
        )

        # Kør Cura-funktionen.
        resultat = await opret_borger(
            page=page,
            session=session,
            cpr=cpr,
            cpr_valideret_via_datafordeleren=True,
        )

        print(resultat)

    finally:
        await session.close()
        print("Browser-session lukket korrekt")


if __name__ == "__main__":
    asyncio.run(main())