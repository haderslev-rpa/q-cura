import asyncio
import re
from typing import Any

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError


CURA_URL = "https://haderslev.cura.columna.dk"

# Stabilt id fra Cura-HTML'en.
CPR_INPUT_SELECTOR = "#citizensearchinput"

# Den almindelige søgeknap.
# :not(.mdi-magnify-plus-outline) forhindrer, at den avancerede
# søgeknap bliver valgt.
SEARCH_BUTTON_SELECTOR = (
    'form#searchform button.mdi-magnify'
    ':not(.mdi-magnify-plus-outline)'
)

# Dialogen, som vises, når borgeren ikke har en journal i Cura.
JOURNAL_DIALOG_SELECTOR = (
    'md-dialog[aria-label="Opret Journal"]:has-text('
    '"Denne borger har ikke en journal i Cura")'
)

# Beskeden, som bekræfter, at Cura er kommet videre efter oprettelsen.
INGEN_ADGANG_BESKED_SELECTOR = (
    "md-toolbar h2"
)


async def opret_borger(
    page: Page,
    session: Any,
    cpr: str,
    *,
    cpr_valideret_via_datafordeleren: bool,
    timeout_ms: int = 10_000,
) -> None:
    """Søg efter et CPR-nummer i Cura og opret borgerens journal.

    Den kaldende proces skal først validere CPR-nummeret via
    Datafordeleren.

    Funktionen gør følgende:

    1. Kontrollerer, at CPR er valideret via Datafordeleren.
    2. Går til Cura.
    3. Åbner CPR-søgningen.
    4. Indtaster CPR-nummeret.
    5. Starter søgningen.
    6. Venter på dialogen "Opret Journal".
    7. Trykker på knappen "Ja".
    8. Venter 2 sekunder.
    9. Venter i op til 25 sekunder på:
       - at dialogen "Opret Journal" lukker
       - at teksten "Du har ikke adgang til denne borger" vises

    Output:
        Funktionen returnerer None, når journalen er oprettet,
        dialogen er lukket, og bekræftelsesbeskeden er vist.

    Exceptions:
        TypeError:
            Hvis cpr_valideret_via_datafordeleren ikke er en bool.

        ValueError:
            Hvis CPR ikke er valideret via Datafordeleren, eller hvis
            CPR-nummeret ikke består af præcis 10 cifre.

        RuntimeError:
            Hvis Cura ikke kan åbnes, CPR ikke indsættes korrekt,
            dialogen "Opret Journal" ikke vises, dialogen ikke lukker,
            eller bekræftelsesbeskeden ikke vises.
    """

    # Kræv en rigtig bool-værdi.
    if type(cpr_valideret_via_datafordeleren) is not bool:
        raise TypeError(
            "cpr_valideret_via_datafordeleren skal være en bool: "
            "True eller False."
        )

    # Stop før Cura betjenes, hvis CPR ikke er valideret.
    if not cpr_valideret_via_datafordeleren:
        raise ValueError(
            "CPR er ikke bekræftet via Datafordeleren. "
            "Den kaldende proces skal validere CPR via Datafordeleren "
            "og sende cpr_valideret_via_datafordeleren=True."
        )

    # Fjern mellemrum og bindestreg fra CPR-nummeret.
    cpr_uden_format = re.sub(r"[\s-]", "", cpr)

    # Dette er kun en formatkontrol.
    # Kontrollen erstatter ikke opslaget via Datafordeleren.
    if not re.fullmatch(r"\d{10}", cpr_uden_format):
        raise ValueError("CPR skal bestå af præcis 10 cifre.")

    # 1. Gå til Cura.
    try:
        await page.goto(
            CURA_URL,
            wait_until="domcontentloaded",
            timeout=timeout_ms,
        )
    except PlaywrightTimeoutError as fejl:
        await session.screenshot(
            page,
            "STEP_1_cura_kunne_ikke_aabnes",
        )

        raise RuntimeError(
            f"Cura kunne ikke åbnes inden for {timeout_ms} ms."
        ) from fejl

    # 2. Vent på søgeknappen, og åbn CPR-søgefeltet.
    search_button = page.locator(SEARCH_BUTTON_SELECTOR).first

    try:
        await search_button.wait_for(
            state="visible",
            timeout=timeout_ms,
        )
    except PlaywrightTimeoutError as fejl:
        await session.screenshot(
            page,
            "STEP_2_soegeknap_ikke_fundet",
        )

        raise RuntimeError(
            "Cura blev åbnet, men søgeknappen blev ikke fundet. "
            "Kontrollér, om brugeren er logget ind."
        ) from fejl

    await search_button.click()

    # 3. Vent på CPR-feltet, og indtast CPR.
    cpr_input = page.locator(CPR_INPUT_SELECTOR)

    try:
        await cpr_input.wait_for(
            state="visible",
            timeout=timeout_ms,
        )
    except PlaywrightTimeoutError as fejl:
        await session.screenshot(
            page,
            "STEP_3_cpr_felt_ikke_fundet",
        )

        raise RuntimeError(
            "CPR-søgefeltet blev ikke vist."
        ) from fejl

    await cpr_input.fill(cpr_uden_format)

    # 4. Læs værdien tilbage fra Cura.
    indtastet_cpr = await cpr_input.input_value()

    # Cura kan automatisk formatere CPR som eksempelvis
    indtastet_cpr_uden_format = re.sub(
        r"[\s-]",
        "",
        indtastet_cpr,
    )

    if indtastet_cpr_uden_format != cpr_uden_format:
        await session.screenshot(
            page,
            "STEP_4_cpr_ikke_indtastet_korrekt",
        )

        raise RuntimeError(
            "CPR blev ikke indsat korrekt i Cura-søgefeltet."
        )

    await session.screenshot(
        page,
        "STEP_4_cpr_indtastet",
    )

    # 5. Start søgningen.
    await cpr_input.press("Enter")

    # 6. Vent på dialogen "Opret Journal".
    journal_dialog = page.locator(JOURNAL_DIALOG_SELECTOR)

    try:
        await journal_dialog.wait_for(
            state="visible",
            timeout=timeout_ms,
        )
    except PlaywrightTimeoutError as fejl:
        await session.screenshot(
            page,
            "STEP_5_opret_journal_dialog_ikke_vist",
        )

        raise RuntimeError(
            "Dialogen 'Opret Journal' blev ikke vist. "
            "Borgeren findes muligvis allerede i Cura."
        ) from fejl

    await session.screenshot(
        page,
        "STEP_5_opret_journal_dialog",
    )

    # 7. Find og tryk på knappen "Ja".
    ja_knap = journal_dialog.get_by_role(
        "button",
        name="Ja",
        exact=True,
    )

    try:
        await ja_knap.wait_for(
            state="visible",
            timeout=timeout_ms,
        )
    except PlaywrightTimeoutError as fejl:
        await session.screenshot(
            page,
            "STEP_6_ja_knap_ikke_fundet",
        )

        raise RuntimeError(
            "Knappen 'Ja' blev ikke fundet i dialogen "
            "'Opret Journal'."
        ) from fejl

    await ja_knap.click()

    # 8. Vent altid 1 sekunder efter trykket på "Ja".
    await page.wait_for_timeout(1_000)

    # Find den præcise besked i en md-toolbar.
    ingen_adgang_besked = (
        page.locator(INGEN_ADGANG_BESKED_SELECTOR)
        .filter(
            has_text=re.compile(
                r"^\s*Du har ikke adgang til denne borger\s*$"
            )
        )
        .first
    )

    # 9. Vent på både dialoglukning og bekræftelsesbesked.
    #
    # Kontrollerne kører samtidig. Dermed er den samlede maksimale
    # ventetid 25 sekunder og ikke 50 sekunder.
    try:
        await asyncio.gather(
            journal_dialog.wait_for(
                state="hidden",
                timeout=25_000,
            ),
            ingen_adgang_besked.wait_for(
                state="visible",
                timeout=25_000,
            ),
        )
    except PlaywrightTimeoutError as fejl:
        await session.screenshot(
            page,
            "STEP_7_oprettelse_ikke_bekraeftet",
        )

        dialog_er_synlig = await journal_dialog.is_visible()
        besked_er_synlig = await ingen_adgang_besked.is_visible()

        if dialog_er_synlig and not besked_er_synlig:
            fejlbesked = (
                "Dialogen 'Opret Journal' er stadig åben, og teksten "
                "'Du har ikke adgang til denne borger' blev ikke vist "
                "inden for 25 sekunder."
            )
        elif dialog_er_synlig:
            fejlbesked = (
                "Teksten 'Du har ikke adgang til denne borger' blev "
                "vist, men dialogen 'Opret Journal' er stadig åben "
                "efter 25 sekunder."
            )
        else:
            fejlbesked = (
                "Dialogen 'Opret Journal' blev lukket, men teksten "
                "'Du har ikke adgang til denne borger' blev ikke vist "
                "inden for 25 sekunder."
            )

        raise RuntimeError(fejlbesked) from fejl

    await session.screenshot(
        page,
        "STEP_7_journal_oprettet_ingen_adgang",
    )