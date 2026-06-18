import time

async def liste_forebyggende_hjaemmebesoeg(
    page,
    session,
    alder: int,
    maaned: str
) -> None:
    """
    Åbner Forebyggende hjemmebesøg og anvender filter
    """

    # ✅ START TIMER (hele udtræk)
    start_time = time.perf_counter()

    # 1. Gå til siden
    url = "https://haderslev.cura.columna.dk/#/preventivevisits/DEFAULT"
    await page.goto(url)
    await page.wait_for_load_state("domcontentloaded")

    await session.screenshot(page, "STEP_1_forebyggende_side")

    # 2. Valider side
    side_titel_selector = 'span.ng-scope:has-text("Forebyggende hjemmebesøg")'
    await page.wait_for_selector(side_titel_selector)

    await session.screenshot(page, "STEP_2_side_valideret")

    # 3. Åbn filter
    await page.click("md-icon.mdi-filter-outline")
    await page.wait_for_selector("md-dialog")

    await session.screenshot(page, "STEP_3_filter_dialog_åben")

    # 4. Udfyld alder
    await page.fill('input[name="minAge"]', str(alder))
    await page.fill('input[name="maxAge"]', str(alder))

    await session.screenshot(page, "STEP_4_alder_udfyldt")

    await page.wait_for_timeout(1000)

    dropdown = page.locator("xpath=//md-select[@aria-label='Fødselsmåned']").first
    await dropdown.wait_for(state="attached")
    await dropdown.scroll_into_view_if_needed()
    await dropdown.click(force=True)

    await page.wait_for_timeout(500)

    await page.wait_for_selector("md-select-menu", state="attached")

    checkbox = page.locator(
        "(//md-select-menu//md-checkbox[@aria-label='Select All'])[last()]"
    )
    await checkbox.scroll_into_view_if_needed()
    await checkbox.click(force=True)

    await session.screenshot(page, "STEP_6_fravaelg_alle")

    await page.wait_for_timeout(500)

    option = page.locator(
        f"(//md-select-menu//md-option[@aria-selected='false' and .//div[contains(normalize-space(), '{maaned}')]])[last()]"
    )

    await option.wait_for(state="attached")
    await option.scroll_into_view_if_needed()
    await option.focus()
    await option.click(force=True)

    await page.wait_for_timeout(500)

    selected_option = page.locator(
        f"(//md-option[@aria-selected='true' and .//div[contains(normalize-space(), '{maaned}')]])[last()]"
    )
    await selected_option.wait_for(state="attached")

    await session.screenshot(page, f"STEP_7_{maaned}_valgt")

    # Luk dropdown
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(500)

    await page.wait_for_selector(
        "//div[contains(@class,'md-select-menu-container') and contains(@class,'md-active')]",
        state="detached"
    )

    await session.screenshot(page, "STEP_8_dropdown_lukket")

    # Klik Søg
    search_btn = page.locator(
        "xpath=//md-dialog//button[.//span[normalize-space()='Søg']]"
    ).first

    await search_btn.wait_for(state="attached")
    await search_btn.scroll_into_view_if_needed()
    await search_btn.click(force=True)

    await page.wait_for_timeout(5000)

    await session.screenshot(page, "STEP_9_soeg_klikket")

    # ✅ Stabil tabel-load
    await page.wait_for_selector("//md-table-container//tr[contains(@class,'md-row')]")

    for _ in range(3):
        await page.mouse.wheel(0, 2000)
        await page.wait_for_timeout(500)

    previous_count = -1

    for _ in range(10):
        rows = page.locator("//md-table-container//tr[contains(@class,'md-row')]")
        current_count = await rows.count()

        if current_count == previous_count:
            break

        previous_count = current_count
        await page.wait_for_timeout(500)

    row_count = current_count

    data = []

    for i in range(row_count):
        row = rows.nth(i)

        cells = row.locator("xpath=.//td")
        cell_count = await cells.count()

        values = []
        for j in range(cell_count):
            text = await cells.nth(j).inner_text()
            values.append(text.strip())

        row_dict = {
            "nextActionDate": values[0] if len(values) > 0 else "",
            "navn": values[1] if len(values) > 1 else "",
            "cpr": values[2] if len(values) > 2 else "",
            "bydel": values[3] if len(values) > 3 else "",
            "område": values[4] if len(values) > 4 else "",
            "adresse": values[5] if len(values) > 5 else "",
            "postnr": values[6] if len(values) > 6 else "",
            "koen": values[7] if len(values) > 7 else "",
            "civilstatus": values[8] if len(values) > 8 else "",
            "alder": values[9] if len(values) > 9 else "",
            "seneste_invitation": values[10] if len(values) > 10 else "",
            "seneste_besoeg": values[11] if len(values) > 11 else "",
            "ansvarlig": values[15] if len(values) > 15 else "",
        }

        data.append(row_dict)

    await session.screenshot(page, "STEP_10_data_hentet")

    # Gå til Mit Overblik
    mit_overblik_btn = page.locator(
        "xpath=//a[.//span[normalize-space()='Mit Overblik']]"
    ).first

    await mit_overblik_btn.wait_for(state="attached")
    await mit_overblik_btn.scroll_into_view_if_needed()
    await mit_overblik_btn.click(force=True)

    await page.wait_for_load_state("domcontentloaded")

    await session.screenshot(page, "STEP_11_mit_overblik")

    # ✅ STOP TIMER (samlet)
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time

    print(f"\n⏱️ Samlet udtrækstid: {elapsed_time:.2f} sekunder")

    return data
"""
    # 5. Sæt fødselsmåned
    maaned_map = {
        "Januar": 1, "Februar": 2, "Marts": 3, "April": 4,
        "Maj": 5, "Juni": 6, "Juli": 7, "August": 8,
        "September": 9, "Oktober": 10, "November": 11, "December": 12
    }

    await page.evaluate(
        
        (maaned) => {
            const comp = document.querySelector('preventive-filter-definition');
            const scope = angular.element(comp).scope();
            scope.$ctrl.filterDefinition.birthMonthList = [maaned];
            scope.$apply();
        }
        ,
        maaned_map[maaned]
    )

    await page.locator('md-select[aria-label="Fødselsmåned"]').focus()
    await session.screenshot(page, f"STEP_5_foedselsmaaned_{maaned}")

    # 6. Søg
    await page.click('button:has-text("Søg")')
    await page.wait_for_timeout(25000)

    await session.screenshot(page, "STEP_6_efter_soeg")

"""