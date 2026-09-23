from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from playwright.async_api import Locator, Page

from q_cura.functionality.haandter_adgang_til_borger_popup import (
    haandter_adgang_til_borger_popup,
)
from playwright.async_api import Locator, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError


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

    Hvis Cura viser dialogen:
    "Du har ikke adgang til denne borger",
    håndteres dialogen automatisk.

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

    await page.goto(
        url,
        wait_until="domcontentloaded",
    )

    print(
        f"Borgerens Hjælpemidler-side er åbnet: "
        f"{citizen_id}"
    )

    # Cura kan vise adgangspopup-dialogen lidt efter,
    # at siden er åbnet.
    adgangspopup_haandteret = (
        await haandter_adgang_til_borger_popup(
            page=page,
            session=session,
            timeout_ms=10_000,
        )
    )

    print(
        "Adgangspopup håndteret: "
        f"{adgangspopup_haandteret}"
    )

    # Når popup-dialogen er håndteret eller ikke blev vist,
    # venter vi på Hjælpemidler-panelet.
    panel_titel = page.locator(
        "mat-expansion-panel-header "
        "mat-panel-title",
        has_text="Hjælpemidler",
    ).first

    try:
        await panel_titel.wait_for(
            state="visible",
            timeout=30_000,
        )

    except PlaywrightTimeoutError as fejl:
        await session.screenshot(
            page,
            "ERROR_hjaelpemidler_panel_ikke_fundet",
        )

        # Ekstra fejlinformation, som fortæller,
        # om en dialog stadig blokerer siden.
        synlige_dialoger = page.locator(
            "md-dialog:visible"
        )

        antal_synlige_dialoger = (
            await synlige_dialoger.count()
        )

        dialog_tekster: list[str] = []

        for index in range(
            antal_synlige_dialoger
        ):
            dialog_tekst = " ".join(
                (
                    await synlige_dialoger
                    .nth(index)
                    .inner_text()
                ).split()
            )

            dialog_tekster.append(
                dialog_tekst[:300]
            )

        if dialog_tekster:
            dialog_beskrivelse = (
                "\nSynlige dialoger:\n - "
                + "\n - ".join(dialog_tekster)
            )
        else:
            dialog_beskrivelse = (
                "\nDer blev ikke fundet nogen "
                "synlige md-dialoger."
            )

        raise RuntimeError(
            "Hjælpemidler-panelet blev ikke vist "
            "efter åbning af borgeren."
            f"{dialog_beskrivelse}"
        ) from fejl

    panel = panel_titel.locator(
        "xpath=ancestor::mat-expansion-panel[1]"
    )

    panel_header = panel.locator(
        "mat-expansion-panel-header"
    )

    panel_er_aabent = (
        await panel_header.get_attribute(
            "aria-expanded"
        )
    )

    if panel_er_aabent != "true":
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

async def vaelg_afslutningsaarsag(
    page: Page,
    session: Any,
    dialog: Locator,
    afslutningsaarsag: str,
    *,
    timeout_ms: int = 15_000,
) -> str:
    """
    Vælger en eksisterende afslutningsårsag i Cura.

    Input:
        page:
            Den aktive Playwright-side.

        session:
            BrowserSession, der bruges til screenshots.

        dialog:
            Playwright-locatoren til ydelsesdialogen.

        afslutningsaarsag:
            Den synlige tekst på den valgmulighed,
            der skal vælges.

            Eksempel:
            "Test"

    Output:
        Returnerer teksten på den valgte afslutningsårsag.

        Eksempel:
        "Test"

    Exceptions:
        ValueError:
            Hvis afslutningsårsagen er tom.

        RuntimeError:
            Hvis feltet ikke findes, ikke bliver aktivt,
            valgmuligheden ikke findes, eller Cura ikke
            registrerer valget.
    """
    afslutningsaarsag = afslutningsaarsag.strip()

    if not afslutningsaarsag:
        raise ValueError(
            "afslutningsaarsag må ikke være tom."
        )

    # Feltet er et Angular Material md-select.
    # aria-label er den mest stabile markering i den HTML,
    # som Cura viser.
    afslutningsaarsag_select = dialog.locator(
        'md-select[aria-label="Afslutningsårsag"]'
    ).first

    try:
        await afslutningsaarsag_select.wait_for(
            state="visible",
            timeout=timeout_ms,
        )

    except PlaywrightTimeoutError as fejl:
        await session.screenshot(
            page,
            "ERROR_afslutningsaarsag_felt_ikke_fundet",
        )

        raise RuntimeError(
            "Feltet 'Afslutningsårsag' blev ikke fundet "
            "i ydelsesdialogen."
        ) from fejl

    print(
        "Feltet 'Afslutningsårsag' blev fundet."
    )

    # Feltet kan være deaktiveret, indtil Cura har
    # registreret slutdatoen.
    felt_er_aktivt = False

    for forsoeg in range(1, 41):
        disabled_attribut = (
            await afslutningsaarsag_select.get_attribute(
                "disabled"
            )
        )

        aria_disabled = (
            await afslutningsaarsag_select.get_attribute(
                "aria-disabled"
            )
        )

        playwright_enabled = (
            await afslutningsaarsag_select.is_enabled()
        )

        if (
            playwright_enabled
            and disabled_attribut is None
            and aria_disabled != "true"
        ):
            felt_er_aktivt = True
            break

        if forsoeg % 4 == 0:
            print(
                "Venter på, at feltet "
                "'Afslutningsårsag' bliver aktivt. "
                f"Kontrol {forsoeg} af 40."
            )

        await page.wait_for_timeout(250)

    if not felt_er_aktivt:
        disabled_attribut = (
            await afslutningsaarsag_select.get_attribute(
                "disabled"
            )
        )

        aria_disabled = (
            await afslutningsaarsag_select.get_attribute(
                "aria-disabled"
            )
        )

        await session.screenshot(
            page,
            "ERROR_afslutningsaarsag_felt_deaktiveret",
        )

        raise RuntimeError(
            "Feltet 'Afslutningsårsag' blev ikke aktivt. "
            "Cura har muligvis ikke registreret slutdatoen. "
            f"disabled={disabled_attribut!r}, "
            f"aria-disabled={aria_disabled!r}."
        )

    print(
        "Feltet 'Afslutningsårsag' er aktivt."
    )

    await afslutningsaarsag_select.scroll_into_view_if_needed()
    await afslutningsaarsag_select.click()

    # Angular Material placerer rullemenuen i overlay-containeren
    # uden for selve dialog-elementet. Derfor søger vi på page
    # og ikke kun inde i dialog.
    aaben_select_container = page.locator(
        "div.md-select-menu-container.md-active"
    ).last

    try:
        await aaben_select_container.wait_for(
            state="visible",
            timeout=timeout_ms,
        )

    except PlaywrightTimeoutError as fejl:
        await session.screenshot(
            page,
            "ERROR_afslutningsaarsag_menu_ikke_aabnet",
        )

        raise RuntimeError(
            "Rullemenuen til 'Afslutningsårsag' "
            "blev ikke åbnet."
        ) from fejl

    # Udskriv de viste valgmuligheder.
    muligheder = aaben_select_container.locator(
        "md-option"
    )

    mulighedstekster: list[str] = []

    for index in range(await muligheder.count()):
        mulighed = muligheder.nth(index)

        tekst = " ".join(
            (await mulighed.inner_text()).split()
        )

        if tekst:
            mulighedstekster.append(tekst)

    print(
        "Tilgængelige afslutningsårsager:"
    )

    for mulighedstekst in mulighedstekster:
        print(
            f"  - {mulighedstekst}"
        )

    # Brug et præcist tekstmatch. re.escape sikrer, at
    # specialtegn i input ikke bliver opfattet som regex.
    valgt_mulighed = aaben_select_container.locator(
        "md-option"
    ).filter(
        has_text=re.compile(
            rf"^\s*{re.escape(afslutningsaarsag)}\s*$",
            re.IGNORECASE,
        )
    ).first

    try:
        await valgt_mulighed.wait_for(
            state="visible",
            timeout=timeout_ms,
        )

    except PlaywrightTimeoutError as fejl:
        await page.keyboard.press("Escape")

        await session.screenshot(
            page,
            "ERROR_afslutningsaarsag_ikke_fundet",
        )

        tilgaengelige = (
            ", ".join(mulighedstekster)
            if mulighedstekster
            else "[ingen muligheder fundet]"
        )

        raise RuntimeError(
            f"Afslutningsårsagen {afslutningsaarsag!r} "
            "blev ikke fundet i rullemenuen. "
            f"Tilgængelige muligheder: {tilgaengelige}"
        ) from fejl

    await valgt_mulighed.scroll_into_view_if_needed()
    await valgt_mulighed.click()

    # Vent på, at rullemenuen lukker.
    try:
        await aaben_select_container.wait_for(
            state="hidden",
            timeout=timeout_ms,
        )

    except PlaywrightTimeoutError as fejl:
        await session.screenshot(
            page,
            "ERROR_afslutningsaarsag_menu_lukkede_ikke",
        )

        raise RuntimeError(
            "Afslutningsårsagen blev klikket, men "
            "rullemenuen lukkede ikke."
        ) from fejl

    # Cura viser den valgte tekst i md-select-value.
    valgt_tekst_locator = afslutningsaarsag_select.locator(
        "md-select-value"
    ).first

    valgt_tekst = " ".join(
        (
            await valgt_tekst_locator.inner_text()
        ).split()
    )

    print(
        f"Valgt afslutningsårsag i Cura: "
        f"{valgt_tekst!r}"
    )

    if (
        _normaliser_tekst(valgt_tekst)
        != _normaliser_tekst(afslutningsaarsag)
    ):
        await session.screenshot(
            page,
            "ERROR_afslutningsaarsag_ikke_registreret",
        )

        raise RuntimeError(
            "Cura registrerede ikke den forventede "
            "afslutningsårsag. "
            f"Forventet: {afslutningsaarsag!r}. "
            f"Fundet: {valgt_tekst!r}."
        )

    # Flyt fokus væk fra select-feltet, så Angular-formularen
    # får mulighed for at færdiggøre sin validering.
    await page.keyboard.press("Tab")
    await page.wait_for_timeout(500)

    await session.screenshot(
        page,
        "STEP_afslutningsaarsag_valgt",
    )

    return valgt_tekst

async def udfyld_slutdato_og_gem(
    page: Page,
    session: Any,
    dialog: Locator,
    slutdato_input: Locator,
    slutdato: str | date | datetime,
    afslutningsaarsag: str,
    stop_foer_gem: bool = True,
) -> None:
    """
    Udfylder slutdato og afslutningsårsag og gemmer ydelsen.

    Input:
        slutdato:
            Datoen forventes i dansk rækkefølge:
            dag, måned, år.

            Punktum er ikke påkrævet.

            Eksempler:
            - "30-9-2026"
            - "30/09/2026"
            - "30.09.2026"

        afslutningsaarsag:
            Teksten på en eksisterende valgmulighed
            i Cura-feltet "Afslutningsårsag".

            Eksempel:
            "Test"

        stop_foer_gem:
            Stopper ved et breakpoint umiddelbart før
            "Gem og bestil", når værdien er True.

    Output:
        Returnerer None.

        Ved succes er slutdato og afslutningsårsag
        registreret, ydelsen gemt og dialogen lukket.
    """
    formateret_slutdato = _format_dansk_dato(
        slutdato
    )

    print(
        f"Slutdato-input {slutdato!r} "
        f"konverteres til {formateret_slutdato!r}."
    )

    await slutdato_input.wait_for(
        state="visible",
        timeout=15_000,
    )

    if await slutdato_input.is_disabled():
        raise RuntimeError(
            "Feltet 'Ydelse afsluttes' er deaktiveret."
        )

    # Skriv datoen som tastetryk, så Cura/Angular
    # registrerer brugerens indtastning.
    await slutdato_input.click()
    await slutdato_input.press("Control+A")
    await slutdato_input.press("Backspace")

    await slutdato_input.press_sequentially(
        formateret_slutdato,
        delay=100,
    )

    faktisk_dato = (
        await slutdato_input.input_value()
    ).strip()

    if faktisk_dato != formateret_slutdato:
        await session.screenshot(
            page,
            "ERROR_slutdato_ikke_indtastet_korrekt",
        )

        raise RuntimeError(
            "Slutdatoen blev ikke indtastet korrekt. "
            f"Forventet: {formateret_slutdato!r}. "
            f"Fundet: {faktisk_dato!r}."
        )

    # Flyt fokus, så Cura registrerer slutdatoen
    # og aktiverer afslutningsårsagen.
    await slutdato_input.press("Tab")
    await page.wait_for_timeout(1_000)

    faktisk_dato_efter_blur = (
        await slutdato_input.input_value()
    ).strip()

    print(
        "Slutdato efter validering: "
        f"{faktisk_dato_efter_blur!r}"
    )

    if faktisk_dato_efter_blur != formateret_slutdato:
        await session.screenshot(
            page,
            "ERROR_slutdato_ikke_registreret",
        )

        raise RuntimeError(
            "Cura registrerede ikke slutdatoen korrekt. "
            f"Forventet: {formateret_slutdato!r}. "
            f"Fundet: {faktisk_dato_efter_blur!r}."
        )

    # Vælg den afslutningsårsag, processen har sendt med.
    valgt_afslutningsaarsag = (
        await vaelg_afslutningsaarsag(
            page=page,
            session=session,
            dialog=dialog,
            afslutningsaarsag=afslutningsaarsag,
        )
    )

    print(
        "Slutdato og afslutningsårsag er udfyldt:"
    )
    print(
        f"  Slutdato: {formateret_slutdato}"
    )
    print(
        f"  Afslutningsårsag: "
        f"{valgt_afslutningsaarsag}"
    )

    # Find knappen via Angular-funktionen.
    gem_og_bestil_knap = dialog.locator(
        "md-dialog-actions button"
        '[ng-click*="SAVE_AND_ORDER"]'
    ).filter(
        has_text="Gem og bestil"
    ).first

    try:
        await gem_og_bestil_knap.wait_for(
            state="visible",
            timeout=15_000,
        )

    except PlaywrightTimeoutError as fejl:
        await session.screenshot(
            page,
            "ERROR_gem_og_bestil_ikke_fundet",
        )

        raise RuntimeError(
            "Knappen 'Gem og bestil' blev ikke fundet "
            "i ydelsesdialogen."
        ) from fejl

    print(
        "Venter på, at 'Gem og bestil' bliver aktiv..."
    )

    knap_er_aktiv = False

    for forsoeg in range(1, 41):
        disabled_attribut = (
            await gem_og_bestil_knap.get_attribute(
                "disabled"
            )
        )

        aria_disabled = (
            await gem_og_bestil_knap.get_attribute(
                "aria-disabled"
            )
        )

        if (
            await gem_og_bestil_knap.is_enabled()
            and disabled_attribut is None
            and aria_disabled != "true"
        ):
            knap_er_aktiv = True
            break

        if forsoeg % 4 == 0:
            print(
                "'Gem og bestil' er endnu ikke aktiv. "
                f"Kontrol {forsoeg} af 40."
            )

        await page.wait_for_timeout(250)

    if not knap_er_aktiv:
        form = dialog.locator(
            'form[name="$ctrl.editCreateActivityForm"]'
        ).first

        form_class = None

        if await form.count() > 0:
            form_class = await form.get_attribute(
                "class"
            )

        await session.screenshot(
            page,
            "ERROR_gem_og_bestil_ikke_aktiv",
        )

        raise RuntimeError(
            "Knappen 'Gem og bestil' blev ikke aktiv "
            "efter valg af slutdato og afslutningsårsag. "
            f"Slutdato: {formateret_slutdato!r}. "
            f"Afslutningsårsag: "
            f"{valgt_afslutningsaarsag!r}. "
            f"Form class: {form_class!r}."
        )

    print(
        "'Gem og bestil' er aktiv."
    )

    await page.wait_for_timeout(500)

    await session.screenshot(
        page,
        "STEP_5_klar_til_gem",
    )

    if stop_foer_gem:
        print(
            "\nSIKKERHEDSSTOP 2:"
        )
        print(
            f"Slutdato: {formateret_slutdato}"
        )
        print(
            f"Afslutningsårsag: "
            f"{valgt_afslutningsaarsag}"
        )
        print(
            "Knappen 'Gem og bestil' er aktiv."
        )
        print(
            "Der er endnu ikke klikket på knappen.\n"
        )

        breakpoint()

    # Kontrollér igen efter breakpointet.
    if not await gem_og_bestil_knap.is_visible():
        raise RuntimeError(
            "Knappen 'Gem og bestil' er ikke længere "
            "synlig efter sikkerhedsbreakpointet."
        )

    if not await gem_og_bestil_knap.is_enabled():
        raise RuntimeError(
            "Knappen 'Gem og bestil' er ikke længere "
            "aktiv efter sikkerhedsbreakpointet."
        )

    print(
        "Klikker på 'Gem og bestil'..."
    )

    await gem_og_bestil_knap.click()

    try:
        await dialog.wait_for(
            state="hidden",
            timeout=30_000,
        )

    except PlaywrightTimeoutError as fejl:
        await session.screenshot(
            page,
            "ERROR_ydelsesdialog_lukkede_ikke",
        )

        raise RuntimeError(
            "Der blev klikket på 'Gem og bestil', "
            "men ydelsesdialogen lukkede ikke."
        ) from fejl

    print(
        "Ydelsesdialogen er lukket. "
        "Ydelsen er gemt."
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
    afslutningsaarsag: str,
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

        afslutningsaarsag:
            En eksisterende valgmulighed i Cura-feltet
            "Afslutningsårsag".

            Eksempel:
            "Klarer sig selv"

        stop_foer_gem:
            Stopper ved breakpoint før Gem og bestil,
            når værdien er True.

    Output:
        En dictionary med citizen_id, ydelsesnavn,
        leverandør, slutdato, afslutningsårsag og status.
    """
    formateret_slutdato = _format_dansk_dato(
        slutdato
    )

    afslutningsaarsag = afslutningsaarsag.strip()

    if not afslutningsaarsag:
        raise ValueError(
            "afslutningsaarsag må ikke være tom."
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
        page=page,
        session=session,
        dialog=dialog,
        slutdato_input=slutdato_input,
        slutdato=formateret_slutdato,
        afslutningsaarsag=afslutningsaarsag,
        stop_foer_gem=stop_foer_gem,
    )

    return {
        "citizen_id": citizen_id,
        "ydelse_navn": ydelse_navn,
        "leverandoer": leverandoer,
        "slutdato": formateret_slutdato,
        "afslutningsaarsag": afslutningsaarsag,
        "status": "afsluttet",
    }