from __future__ import annotations

from typing import Any

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError


ADGANG_DIALOG_TITEL = (
    "Du har ikke adgang til denne borger"
)

ADGANGSBEGRUNDELSE = (
    "Jeg har borgeren i aktuel behandling "
    "eller opfølgningsansvar"
)


async def haandter_adgang_til_borger_popup(
    page: Page,
    session: Any,
    *,
    timeout_ms: int = 10_000,
) -> bool:
    """
    Håndterer Cura-dialogen om manglende adgang,
    hvis dialogen vises.

    Funktionen gør følgende:

    1. Søger efter dialogen med overskriften:
       "Du har ikke adgang til denne borger".

    2. Hvis dialogen ikke vises, fortsætter
       funktionen uden fejl.

    3. Vælger begrundelsen:
       "Jeg har borgeren i aktuel behandling
       eller opfølgningsansvar".

    4. Kontrollerer, at radioknappen er valgt.

    5. Finder Gem-knappen via dialogens handlingsområde
       og knappens ng-click-attribut.

    6. Klikker på Gem.

    7. Venter på, at dialogen lukker.

    Output:
        True:
            Dialogen blev fundet og håndteret.

        False:
            Dialogen blev ikke vist.
    """

    # Dialogens aria-label indeholder ikke nødvendigvis
    # hele overskriften. Derfor finder vi først den
    # synlige overskrift.
    dialog_overskrift = page.locator(
        "md-dialog md-toolbar h2"
    ).filter(
        has_text=ADGANG_DIALOG_TITEL
    ).first

    try:
        await dialog_overskrift.wait_for(
            state="visible",
            timeout=timeout_ms,
        )

    except PlaywrightTimeoutError:
        print(
            "Ingen adgangspopup blev vist. "
            "Flowet fortsætter."
        )

        return False

    # Find den md-dialog, som overskriften tilhører.
    dialog = dialog_overskrift.locator(
        "xpath=ancestor::md-dialog[1]"
    )

    await dialog.wait_for(
        state="visible",
        timeout=timeout_ms,
    )

    print(
        "Adgangspopup blev vist."
    )

    await session.screenshot(
        page,
        "STEP_adgangspopup_vist",
    )

    # Radioknappen har den fulde tekst i aria-label.
    begrundelse = dialog.locator(
        "md-radio-button"
        f'[aria-label="{ADGANGSBEGRUNDELSE}"]'
    ).first

    try:
        await begrundelse.wait_for(
            state="visible",
            timeout=timeout_ms,
        )

    except PlaywrightTimeoutError as fejl:
        await session.screenshot(
            page,
            "ERROR_adgangsbegrundelse_ikke_fundet",
        )

        raise RuntimeError(
            "Adgangspopup blev vist, men begrundelsen "
            f"{ADGANGSBEGRUNDELSE!r} blev ikke fundet."
        ) from fejl

    await begrundelse.scroll_into_view_if_needed()
    await begrundelse.click()

    # Vent på, at Angular registrerer markeringen.
    begrundelse_er_valgt = False

    for forsoeg in range(1, 11):
        aria_checked = (
            await begrundelse.get_attribute(
                "aria-checked"
            )
        )

        if aria_checked == "true":
            begrundelse_er_valgt = True
            break

        await page.wait_for_timeout(200)

    if not begrundelse_er_valgt:
        await session.screenshot(
            page,
            "ERROR_adgangsbegrundelse_ikke_valgt",
        )

        raise RuntimeError(
            "Adgangsbegrundelsen blev fundet, "
            "men Cura markerede ikke valget."
        )

    print(
        "Valgt adgangsbegrundelse: "
        f"{ADGANGSBEGRUNDELSE}"
    )

    await session.screenshot(
        page,
        "STEP_adgangsbegrundelse_valgt",
    )

    # Knappen indeholder et ikon med aria-label="Save".
    # Derfor kan get_by_role(name="Gem") opfatte knappens
    # navn som "Save" i stedet for "Gem".
    #
    # Vi finder derfor knappen via:
    # 1. Dialogens handlingsområde
    # 2. Den stabile ng-click-attribut
    # 3. Den synlige tekst Gem
    gem_knap = dialog.locator(
        "md-dialog-actions button"
        '[ng-click*="submitLogEntry"]'
    ).filter(
        has_text="Gem"
    ).first

    try:
        await gem_knap.wait_for(
            state="visible",
            timeout=timeout_ms,
        )

    except PlaywrightTimeoutError as fejl:
        await session.screenshot(
            page,
            "ERROR_adgangspopup_gem_ikke_fundet",
        )

        # Hent knapperne i dialogens handlingsområde.
        # Oplysningerne medtages i fejlbeskeden, så en
        # fremtidig ændring i Cura er lettere at finde.
        dialog_knapper = dialog.locator(
            "md-dialog-actions button"
        )

        knap_beskrivelser: list[str] = []

        for index in range(
            await dialog_knapper.count()
        ):
            knap = dialog_knapper.nth(index)

            knap_tekst = " ".join(
                (
                    await knap.inner_text()
                ).split()
            )

            knap_ng_click = (
                await knap.get_attribute(
                    "ng-click"
                )
            )

            knap_beskrivelser.append(
                f"tekst={knap_tekst!r}, "
                f"ng-click={knap_ng_click!r}"
            )

        fundne_knapper = (
            "\n - ".join(knap_beskrivelser)
            if knap_beskrivelser
            else "[ingen knapper fundet]"
        )

        raise RuntimeError(
            "Knappen 'Gem' blev ikke fundet i "
            "adgangspopup-dialogen."
            f"\nFundne dialogknapper:\n - "
            f"{fundne_knapper}"
        ) from fejl

    print(
        "Gem-knappen blev fundet."
    )

    # Vent kort på, at formularen bliver gyldig.
    gem_knap_er_aktiv = False

    for forsoeg in range(1, 21):
        if await gem_knap.is_enabled():
            gem_knap_er_aktiv = True
            break

        if forsoeg % 5 == 0:
            print(
                "Venter på, at Gem-knappen "
                "bliver aktiv..."
            )

        await page.wait_for_timeout(250)

    if not gem_knap_er_aktiv:
        disabled_attribut = (
            await gem_knap.get_attribute(
                "disabled"
            )
        )

        aria_disabled = (
            await gem_knap.get_attribute(
                "aria-disabled"
            )
        )

        await session.screenshot(
            page,
            "ERROR_adgangspopup_gem_deaktiveret",
        )

        raise RuntimeError(
            "Knappen 'Gem' blev fundet, men den "
            "er stadig deaktiveret efter valg af "
            "begrundelse. "
            f"disabled={disabled_attribut!r}, "
            f"aria-disabled={aria_disabled!r}."
        )

    print(
        "Klikker på 'Gem' i adgangspopup."
    )

    await gem_knap.click()

    try:
        await dialog.wait_for(
            state="hidden",
            timeout=15_000,
        )

    except PlaywrightTimeoutError as fejl:
        await session.screenshot(
            page,
            "ERROR_adgangspopup_lukkede_ikke",
        )

        raise RuntimeError(
            "Der blev klikket på 'Gem', men "
            "adgangspopup-dialogen lukkede ikke."
        ) from fejl

    print(
        "Adgangspopup blev gemt og lukket."
    )

    await session.screenshot(
        page,
        "STEP_adgangspopup_lukket",
    )

    return True