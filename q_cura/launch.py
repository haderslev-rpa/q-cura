from automation_server_client import AutomationServer, Credential
import asyncio


async def launch_cura(page, session):
    """
    Åbner Cura og logger ind

    - page (objekt – browser-fane) oprettes i main
    - session (objekt – BrowserSession) bruges til dokumentation
    """

    URL = "https://haderslev.cura.columna.dk"

    # Hent credentials
    AutomationServer.from_environment()
    credential = Credential.get_credential("API_CURA")

    # Gå til Cura
    await page.goto(URL)
    await page.wait_for_load_state("domcontentloaded")

    # Screenshot (kun hvis debug=True eller always=True)
    await session.recorder.screenshot(page, "STEP_1_startside")

    # Login
    await page.fill("#username", credential.username)
    await page.fill("#password", credential.password)

    await session.recorder.screenshot(page, "STEP_2_før_login")

    await page.click("#kc-login")
    await asyncio.sleep(1)

    await session.recorder.screenshot(page, "STEP_3_efter_login")

    await page.wait_for_selector("#kc-login", state="detached")

    print("✅ Login gennemført")