from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from playwright.async_api import Locator, Page


BASE_URL = "https://haderslev.cura.columna.dk"
LEVERANDOER_SUFFIX = "(Eksterne ydelsesleverandører)"


def _normaliser_tekst(value: str | None) -> str:
    """
    Samler mellemrum og gør tekst sammenlignelig uden forskel
    på store og små bogstaver.
    """
    return " ".join((value or "").split()).casefold()


def _normaliser_leverandoer(value: str | None) -> str:
    """
    Normaliserer et leverandørnavn og fjerner Cura-suffikset.

    Funktionen fjerner kun teksten:
    "(Eksterne ydelsesleverandører)".

    Andre parenteser bevares, fordi eksempelvis
    "(Hjælpemidler)" er en del af leverandørnavnet.

    Output:
        Et normaliseret leverandørnavn, som kan bruges
        til sammenligning.
    """
    tekst = " ".join((value or "").split())

    tekst = re.sub(
        rf"\s*{re.escape(LEVERANDOER_SUFFIX)}\s*$",
        "",
        tekst,
        flags=re.IGNORECASE,
    )

    return tekst.strip().casefold()


def _leverandoer_matcher(
    forventet: str,
    faktisk: str,
) -> bool:
    """
    Sammenligner et kort og et fuldt leverandørnavn efter
    fjernelse af Cura-suffikset.

    Output:
        True, hvis leverandørnavnene matcher.
        False, hvis leverandørnavnene ikke matcher.
    """
    forventet_normaliseret = _normaliser_leverandoer(
        forventet
    )

    faktisk_normaliseret = _normaliser_leverandoer(
        faktisk
    )

    return bool(forventet_normaliseret) and (
        forventet_normaliseret
        == faktisk_normaliseret
    )


def _format_dansk_dato(
    value: str | date | datetime,
) -> str:
    """
    Konverterer et dansk dato-input til Cura-formatet DD.MM.YYYY.

    Inputbeskrivelse:
        Datoen forventes i dansk rækkefølge:
        dag, måned, år.

        Punktum er ikke påkrævet.

        Accepterede eksempler:
        - "30-9-2026"
        - "30/09/2026"
        - "30.09.2026"
        - date(2026, 9, 30)
        - datetime(2026, 9, 30)

    Output:
        En tekststreng i formatet DD.MM.YYYY,
        eksempelvis "30.09.2026".
    """
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y")

    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")

    tekst = str(value).strip()

    for separator in (".", "-", "/"):
        dele = tekst.split(separator)

        if len(dele) != 3:
            continue

        try:
            dag, maaned, aar = (
                int(del_value)
                for del_value in dele
            )

            if aar < 100:
                aar += 2000

            formateret_dato = date(
                aar,
                maaned,
                dag,
            )

            return formateret_dato.strftime(
                "%d.%m.%Y"
            )

        except ValueError:
            continue

    raise ValueError(
        f"Ugyldig dansk dato: {value!r}. "
        "Skriv datoen i dansk rækkefølge "
        "dag-måned-år, eksempelvis 30-9-2026, "
        "30/09/2026 eller 30.09.2026."
    )


async def aaben_borgerens_ydelser(
    page: Page,
    session: Any,
    citizen_id: str,
) -> Locator:
    """
    Åbner borgerens side med Hjælpemidler.

    Output:
        Returnerer Playwright-locatoren til det åbne
        Hjælpemidler-panel.
    """
    citizen_id = citizen_id.strip()

    if not citizen_id:
        raise ValueError(
            "citizen_id må ikke være tomt."
        )

    url = (
        f"{BASE_URL}/#/citizen/{citizen_id}"
        "/my-life/activities"
        "?caseTypes=Hj%C3%A6lpemidler"
    )

    await page.goto(url)
    await page.wait_for_load_state(
        "domcontentloaded"
    )

    panel_titel = page.locator(
        "mat-expansion-panel-header "
        "mat-panel-title",
        has_text="Hjælpemidler",
    ).first

    await panel_titel.wait_for(
        state="visible",
        timeout=30_000,
    )

    panel = panel_titel.locator(
        "xpath=ancestor::mat-expansion-panel[1]"
    )

    panel_header = panel.locator(
        "mat-expansion-panel-header"
    )

    if (
        await panel_header.get_attribute(
            "aria-expanded"
        )
        != "true"
    ):
        await panel_header.click()

    await panel.locator(
        ".mat-expansion-panel-body"
    ).wait_for(
        state="visible",
        timeout=15_000,
    )

    await session.screenshot(
        page,
        "STEP_1_hjaelpemidler_aabnet",
    )

    return panel


async def hent_hjaelpemidler(
    panel: Locator,
    session: Any | None = None,
    page: Page | None = None,
) -> list[dict[str, str]]:
    """
    Trækker de viste ydelser ud fra Hjælpemidler-panelet.

    Output:
        En liste med navn, leverandør og aktiv periode
        for hver ydelse.
    """
    rows = panel.locator(
        "cura-activity-overview-item"
    )

    await rows.first.wait_for(
        state="visible",
        timeout=30_000,
    )

    resultater: list[dict[str, str]] = []

    for index in range(await rows.count()):
        row = rows.nth(index)

        navn = " ".join(
            (
                await row.locator(
                    ".web-activity-name"
                ).first.inner_text()
            ).split()
        )

        leverandoer_locator = row.locator(
            ".suppliers-content"
        ).first

        leverandoer = ""

        if await leverandoer_locator.count() > 0:
            leverandoer = " ".join(
                (
                    await leverandoer_locator.inner_text()
                ).split()
            )

        periode_locator = row.locator(
            ".mat-mdc-list-item-line",
            has_text="Aktiv periode",
        ).first

        aktiv_periode = ""

        if await periode_locator.count() > 0:
            aktiv_periode = " ".join(
                (
                    await periode_locator.inner_text()
                ).split()
            )

            aktiv_periode = (
                aktiv_periode
                .removeprefix("Aktiv periode:")
                .strip()
            )

        resultater.append(
            {
                "navn": navn,
                "leverandoer": leverandoer,
                "aktiv_periode": aktiv_periode,
            }
        )

    if (
        session is not None
        and page is not None
    ):
        await session.screenshot(
            page,
            "STEP_2_hjaelpemidler_hentet",
        )

    return resultater


async def find_ydelse(
    panel: Locator,
    ydelse_navn: str,
    leverandoer: str,
) -> Locator:
    """
    Finder præcis én ydelse ud fra navn og leverandør.

    Output:
        Returnerer Playwright-locatoren til den fundne
        ydelsesrække.
    """
    rows = panel.locator(
        "cura-activity-overview-item"
    )

    matches: list[Locator] = []
    fundne: list[str] = []

    for index in range(await rows.count()):
        row = rows.nth(index)

        navn = " ".join(
            (
                await row.locator(
                    ".web-activity-name"
                ).first.inner_text()
            ).split()
        )

        leverandoer_locator = row.locator(
            ".suppliers-content"
        ).first

        fundet_leverandoer = ""

        if await leverandoer_locator.count() > 0:
            fundet_leverandoer = " ".join(
                (
                    await leverandoer_locator.inner_text()
                ).split()
            )

        fundne.append(
            f"{navn} | Leverandør: "
            f"{fundet_leverandoer or '[ingen]'}"
        )

        navn_matcher = (
            _normaliser_tekst(navn)
            == _normaliser_tekst(ydelse_navn)
        )

        leverandoer_matcher = (
            _leverandoer_matcher(
                leverandoer,
                fundet_leverandoer,
            )
        )

        if (
            navn_matcher
            and leverandoer_matcher
        ):
            matches.append(row)

    if len(matches) != 1:
        oversigt = (
            "\n - ".join(fundne)
            if fundne
            else "[ingen ydelser fundet]"
        )

        raise RuntimeError(
            "Forventede præcis én ydelse med det "
            "angivne navn og leverandør, men fandt "
            f"{len(matches)}. Fundne ydelser:\n"
            f" - {oversigt}"
        )

    return matches[0]


async def aaben_og_valider_ydelse(
    page: Page,
    session: Any,
    ydelse_row: Locator,
    ydelse_navn: str,
    leverandoer: str,
) -> Locator:
    """
    Åbner ydelsen og validerer navn og leverandør.

    Output:
        Returnerer Playwright-locatoren til den åbne
        ydelsesdialog.
    """
    clickable_area = ydelse_row.locator(
        "div.mat-ripple.clickable"
    ).first

    await clickable_area.click()

    dialog = page.locator(
        "#edit-activity-dialog"
    )

    await dialog.wait_for(
        state="visible",
        timeout=20_000,
    )

    ydelse_input = dialog.locator(
        "md-input-container:"
        "has(label:text-is('Ydelse')) input"
    ).first

    await ydelse_input.wait_for(
        state="visible",
        timeout=10_000,
    )

    faktisk_navn = (
        await ydelse_input.input_value()
    )

    if (
        _normaliser_tekst(faktisk_navn)
        != _normaliser_tekst(ydelse_navn)
    ):
        raise RuntimeError(
            "Forkert ydelse blev åbnet. "
            f"Forventet: {ydelse_navn!r}. "
            f"Åbnet: {faktisk_navn!r}."
        )

    leverandoer_input = dialog.locator(
        "input[aria-label='Leverandør']"
    ).first

    await leverandoer_input.wait_for(
        state="attached",
        timeout=10_000,
    )

    faktisk_leverandoer = (
        await leverandoer_input.input_value()
    )

    print(
        f"Leverandør fra oversigten: "
        f"{leverandoer}"
    )
    print(
        f"Leverandør fra dialogen: "
        f"{faktisk_leverandoer}"
    )
    print(
        "Normaliseret leverandør fra dialogen: "
        f"{_normaliser_leverandoer(faktisk_leverandoer)}"
    )

    if not _leverandoer_matcher(
        leverandoer,
        faktisk_leverandoer,
    ):
        raise RuntimeError(
            "Ydelsens leverandør matcher ikke efter "
            f"fjernelse af {LEVERANDOER_SUFFIX!r}. "
            f"Forventet: {leverandoer!r}. "
            f"Fundet: {faktisk_leverandoer!r}."
        )

    await session.screenshot(
        page,
        "STEP_3_ydelse_valideret",
    )

    return dialog


async def aktiver_redigering(
    page: Page,
    session: Any,
    dialog: Locator,
) -> Locator:
    """
    Klikker på redigeringsblyanten.

    Output:
        Returnerer Playwright-locatoren til feltet
        Ydelse afsluttes.
    """
    rediger_knap = dialog.locator(
        "button.mdi-pencil"
    ).first

    await rediger_knap.wait_for(
        state="visible",
        timeout=10_000,
    )

    await rediger_knap.click()

    slutdato_input = dialog.locator(
        "date-picker-deprecated:"
        "has(mat-label:text-is("
        "'Ydelse afsluttes')) input"
    ).first

    await slutdato_input.wait_for(
        state="visible",
        timeout=15_000,
    )

    if await slutdato_input.is_disabled():
        raise RuntimeError(
            "Feltet 'Ydelse afsluttes' er stadig "
            "deaktiveret efter Rediger."
        )

    await session.screenshot(
        page,
        "STEP_4_redigering_aktiveret",
    )

    return slutdato_input


async def udfyld_slutdato_og_gem(
    page: Page,
    session: Any,
    dialog: Locator,
    slutdato_input: Locator,
    slutdato: str | date | datetime,
    stop_foer_gem: bool = True,
) -> None:
    """
    Udfylder slutdatoen og gemmer ydelsen.

    Input:
        page:
            Den aktive Playwright-side.

        session:
            BrowserSession, som blandt andet bruges til screenshots.

        dialog:
            Playwright-locatoren til ydelsesdialogen.

        slutdato_input:
            Playwright-locatoren til feltet "Ydelse afsluttes".

        slutdato:
            Datoen forventes i dansk rækkefølge:
            dag, måned, år.

            Punktum er ikke påkrævet.

            Gyldige eksempler:
            - "30-9-2026"
            - "30/09/2026"
            - "30.09.2026"
            - date(2026, 9, 30)
            - datetime(2026, 9, 30)

        stop_foer_gem:
            Hvis værdien er True, stopper funktionen ved et breakpoint,
            umiddelbart før der klikkes på "Gem og bestil".

    Output:
        Funktionen returnerer None.

        Ved succes:
        - Slutdatoen er udfyldt.
        - "Gem og bestil" er blevet aktiv.
        - Sikkerhedsbreakpointet er passeret.
        - Der er klikket på "Gem og bestil".
        - Ydelsesdialogen er lukket.
    """
    formateret_slutdato = _format_dansk_dato(
        slutdato
    )

    print(
        f"Slutdato-input {slutdato!r} "
        f"konverteres til {formateret_slutdato!r}."
    )

    # Kontrollér, at slutdatofeltet stadig er tilgængeligt.
    await slutdato_input.wait_for(
        state="visible",
        timeout=15_000,
    )

    if await slutdato_input.is_disabled():
        raise RuntimeError(
            "Feltet 'Ydelse afsluttes' er deaktiveret, "
            "og slutdatoen kan derfor ikke udfyldes."
        )

    # Udfyld datoen i det format, Cura forventer.
    await slutdato_input.fill(
        formateret_slutdato
    )

    # Flyt fokus væk fra feltet.
    # Det får Angular til at registrere ændringen.
    await slutdato_input.press("Tab")

    # Giv Cura et kort øjeblik til at validere feltet.
    await page.wait_for_timeout(500)

    faktisk_dato = (
        await slutdato_input.input_value()
    ).strip()

    print(
        f"Slutdatofeltet indeholder nu: "
        f"{faktisk_dato!r}"
    )

    if faktisk_dato != formateret_slutdato:
        raise RuntimeError(
            "Cura beholdt ikke den forventede slutdato. "
            f"Forventet: {formateret_slutdato!r}. "
            f"Feltet indeholder: {faktisk_dato!r}."
        )

    gem_knap = dialog.get_by_role(
        "button",
        name="Gem og bestil",
        exact=True,
    )

    await gem_knap.wait_for(
        state="visible",
        timeout=10_000,
    )

    print(
        "Venter på, at knappen "
        "'Gem og bestil' bliver aktiv..."
    )

    # Vent op til 15 sekunder på, at Angular aktiverer knappen.
    #
    # Vi kontrollerer hvert halve sekund.
    # Dette erstatter page.wait_for_function(), som gav fejlen
    # med det positionelle argument.
    antal_forsoeg = 30
    ventetid_mellem_forsoeg_ms = 500

    for forsoeg in range(
        1,
        antal_forsoeg + 1,
    ):
        if await gem_knap.is_enabled():
            print(
                "'Gem og bestil' er nu aktiv."
            )
            break

        if forsoeg % 5 == 0:
            print(
                "Knappen er endnu ikke aktiv. "
                f"Kontrol {forsoeg} af "
                f"{antal_forsoeg}."
            )

        await page.wait_for_timeout(
            ventetid_mellem_forsoeg_ms
        )

    else:
        disabled_attribute = (
            await gem_knap.get_attribute(
                "disabled"
            )
        )

        aria_disabled_attribute = (
            await gem_knap.get_attribute(
                "aria-disabled"
            )
        )

        button_class = (
            await gem_knap.get_attribute(
                "class"
            )
        )

        await session.screenshot(
            page,
            "ERROR_gem_og_bestil_ikke_aktiv",
        )

        raise RuntimeError(
            "Knappen 'Gem og bestil' blev ikke aktiv "
            "efter udfyldelse af slutdatoen. "
            f"Slutdato i feltet: {faktisk_dato!r}. "
            f"disabled-attribut: {disabled_attribute!r}. "
            f"aria-disabled: {aria_disabled_attribute!r}. "
            f"CSS-klasser: {button_class!r}."
        )

    await session.screenshot(
        page,
        "STEP_5_klar_til_gem",
    )

    if stop_foer_gem:
        print(
            "\nSIKKERHEDSSTOP 2:"
        )
        print(
            "Kontrollér borger, ydelse, leverandør "
            "og slutdato i browseren."
        )
        print(
            f"Slutdato: {formateret_slutdato}"
        )
        print(
            "Knappen 'Gem og bestil' er aktiv."
        )
        print(
            "Der er endnu ikke klikket på knappen."
        )
        print(
            "Fortsæt kun debuggeren, hvis alle "
            "oplysninger er korrekte.\n"
        )

        breakpoint()

    # Kontrollér igen efter breakpointet.
    # Siden kan i princippet have ændret sig, mens testen var stoppet.
    if not await gem_knap.is_visible():
        raise RuntimeError(
            "Knappen 'Gem og bestil' er ikke længere synlig "
            "efter sikkerhedsbreakpointet."
        )

    if not await gem_knap.is_enabled():
        raise RuntimeError(
            "Knappen 'Gem og bestil' er ikke længere aktiv "
            "efter sikkerhedsbreakpointet."
        )

    print(
        "Klikker på 'Gem og bestil'..."
    )

    await gem_knap.click()

    # Vent på, at dialogen lukker.
    # Det er bekræftelsen på, at Cura har behandlet klikket.
    await dialog.wait_for(
        state="hidden",
        timeout=30_000,
    )

    print(
        "Ydelsesdialogen er lukket."
    )

    await session.screenshot(
        page,
        "STEP_6_ydelse_gemt",
    )


async def afslut_ydelse(
    page: Page,
    session: Any,
    citizen_id: str,
    ydelse_navn: str,
    leverandoer: str,
    slutdato: str | date | datetime,
    stop_foer_gem: bool = True,
) -> dict[str, str]:
    """
    Åbner, finder, validerer og afslutter én ydelse.

    Input:
        citizen_id:
            Borgerens Cura-id.

        ydelse_navn:
            Det præcise navn på ydelsen.

        leverandoer:
            Det korte leverandørnavn fra
            Hjælpemidler-oversigten.

        slutdato:
            Dansk dato i rækkefølgen dag, måned, år.

            Punktum er ikke påkrævet.

            Eksempler:
            - "30-9-2026"
            - "30/09/2026"
            - "30.09.2026"

        stop_foer_gem:
            Stopper ved breakpoint før Gem og bestil,
            når værdien er True.

    Output:
        En dictionary med citizen_id, ydelsesnavn,
        leverandør, formateret slutdato og status.
    """
    formateret_slutdato = (
        _format_dansk_dato(slutdato)
    )

    panel = await aaben_borgerens_ydelser(
        page,
        session,
        citizen_id,
    )

    ydelser = await hent_hjaelpemidler(
        panel,
        session,
        page,
    )

    print(
        f"Fandt {len(ydelser)} ydelse(r) "
        "i Hjælpemidler-panelet:"
    )

    for ydelse in ydelser:
        print(
            f"  - {ydelse['navn']} | "
            f"{ydelse['leverandoer'] or '[ingen leverandør]'} | "
            f"{ydelse['aktiv_periode']}"
        )

    ydelse_row = await find_ydelse(
        panel,
        ydelse_navn,
        leverandoer,
    )

    dialog = await aaben_og_valider_ydelse(
        page,
        session,
        ydelse_row,
        ydelse_navn,
        leverandoer,
    )

    slutdato_input = await aktiver_redigering(
        page,
        session,
        dialog,
    )

    await udfyld_slutdato_og_gem(
        page,
        session,
        dialog,
        slutdato_input,
        formateret_slutdato,
        stop_foer_gem=stop_foer_gem,
    )

    return {
        "citizen_id": citizen_id,
        "ydelse_navn": ydelse_navn,
        "leverandoer": leverandoer,
        "slutdato": formateret_slutdato,
        "status": "afsluttet",
    }