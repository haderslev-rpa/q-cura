import asyncio

from q_haderslev_vbo.playwright.browser_session import (
    BrowserSession,
)
from q_cura.functionality.afslut_ydelse import (
    afslut_ydelse,
)
from q_cura.functionality.launch import (
    launch_cura,
)


# Udfyld testdata meget omhyggeligt før kørsel.
CITIZEN_ID = (
    "0a8a6458-695b-4c43-ba4f-6b8705600c74"
)

YDELSE_NAVN = (
    "Kropsbårne hjælpemidler § 112 (Paryk)"
)

# Brug det korte leverandørnavn, som står
# i Hjælpemidler-oversigten.
LEVERANDOER = "(Hjælpemidler) Sahva A/S"

# Dansk dato i rækkefølgen dag, måned, år.
# Punktum er ikke nødvendigt.
SLUTDATO = "30-9-2026"

# Skal være en eksisterende valgmulighed
# i Cura-feltet "Afslutningsårsag".
AFSLUTNINGSAARSAG = "Klarer sig selv"


async def main() -> None:
    """
    Kører en manuel sikkerhedstest af afslut_ydelse.

    Output:
        Udskriver resultat-dictionary ved succes.

    Sikkerhed:
        Testen stopper efter login og igen umiddelbart
        før Gem og bestil.
    """
    session = BrowserSession(
        headless=False,
        debug=True,
        video=True,
    )

    await session.start()

    page = await session.new_page()

    try:
        await launch_cura(
            page=page,
            session=session,
        )

        print(
            "\nSIKKERHEDSSTOP 1: "
            "Kontrollér testdata:"
        )

        print(
            f"Citizen ID: {CITIZEN_ID}"
        )

        print(
            f"Ydelse: {YDELSE_NAVN}"
        )

        print(
            f"Kort leverandørnavn: "
            f"{LEVERANDOER}"
        )

        print(
            f"Dansk slutdato-input: "
            f"{SLUTDATO}"
        )

        print(
            f"Afslutningsårsag: "
            f"{AFSLUTNINGSAARSAG}\n"
        )

        # FAST BREAKPOINT 1:
        # Testen stopper altid her ved normal
        # debug-kørsel i VS Code.
        breakpoint()

        resultat = await afslut_ydelse(
            page=page,
            session=session,
            citizen_id=CITIZEN_ID,
            ydelse_navn=YDELSE_NAVN,
            leverandoer=LEVERANDOER,
            slutdato=SLUTDATO,
            afslutningsaarsag=AFSLUTNINGSAARSAG,

            # FAST BREAKPOINT 2 ligger inde i
            # funktionen lige før Gem og bestil.
            stop_foer_gem=True,
        )

        print(
            "\nYdelsen blev afsluttet:"
        )

        print(resultat)

    finally:
        await session.close()

        print(
            "Browser-session lukket korrekt"
        )


if __name__ == "__main__":
    asyncio.run(main())