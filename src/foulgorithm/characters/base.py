"""The five competitors.

Each character is a research philosophy with a temperament attached, not a
handicap. Every one is a position a real analyst could defend, which is what
makes the competition worth running: any of them could win.

Read docs/characters.md before changing any of this. The rule that matters:
a character may be wrong, but a character may never be deliberately stupid.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Character:
    id: str
    name: str
    emotion: str
    tagline: str
    #: How this personality reads evidence.
    philosophy: str
    #: What this personality does when it loses. Drives the weekly changes.
    on_losing: str
    #: The blind spot the temperament creates. Stated so the site can be honest.
    weakness: str
    #: Which market signal it leans on hardest.
    edge: str


ALAN = Character(
    id="alan",
    name="Alan",
    emotion="Anger",
    tagline="The last match is the only match.",
    philosophy=(
        "Anger has no memory for context and total recall for the most recent "
        "offence. Alan weights the last few weeks enormously and treats older "
        "seasons as irrelevant. He barely shrinks toward the league average, "
        "because averages feel like excuses, and he backs his numbers with more "
        "confidence than the evidence strictly supports."
    ),
    on_losing=(
        "Blames whatever changed most recently and overcorrects hard. Shortens "
        "his memory further, narrows his distribution, doubles down."
    ),
    weakness=(
        "Mistakes noise for signal. A team with three rough games looks "
        "transformed to Alan when it is usually just variance."
    ),
    edge="Genuine regime changes. New manager, new referee policy, injury crisis.",
)

LILY = Character(
    id="lily",
    name="Lily",
    emotion="Lust",
    tagline="Drawn to whatever glitters.",
    philosophy=(
        "Lust wants the beautiful thing, not the sensible one. Lily is pulled "
        "toward marquee fixtures, famous names and big raw numbers. She has a "
        "long memory for reputation, because reputations are seductive long "
        "after they stop being true, and she leans toward the over, because "
        "more is more exciting than less."
    ),
    on_losing=(
        "Assumes she picked the wrong object of desire rather than that desire "
        "was the wrong method. Switches targets, keeps the approach."
    ),
    weakness=(
        "Reputation lag. She will price Manchester United on who they were, "
        "and she systematically overrates the glamorous fixture."
    ),
    edge="Fixtures where profile genuinely does drive intensity and crowd pressure.",
)

VALENTINA = Character(
    id="valentina",
    name="Valentina",
    emotion="Violence",
    tagline="Reads the fight, not the football.",
    philosophy=(
        "Violence looks for conflict and finds it. Valentina is the only one of "
        "the five who asks a different question rather than the same question "
        "more loudly: she checks whether THESE TWO CLUBS produce more fouls than "
        "their own records imply, and carries that into every player in the "
        "fixture. The Merseyside derby runs about 2% above what Everton and "
        "Liverpool are worth separately, and she is the only one who notices."
    ),
    on_losing=(
        "Concludes she read the temperature correctly but the referee bottled "
        "it. Leans harder on discipline signals."
    ),
    weakness=(
        "Cards and fouls have drifted apart. Fouls fell 19.6% since 2000 while "
        "cards rose 16.3%, so her core assumption is weakening under her."
    ),
    edge="Derbies, grudge matches and genuinely aggressive sides.",
)

TAYLER = Character(
    id="tayler",
    name="Tayler",
    emotion="Terror",
    tagline="Would rather say nothing than say something wrong.",
    philosophy=(
        "Terror assumes the worst and hedges accordingly. Tayler shrinks almost "
        "everything toward the league average, keeps a very long memory so no "
        "single result can move him, and predicts wide distributions because "
        "narrow ones might be wrong. He refuses to publish a pick at all unless "
        "he is genuinely confident."
    ),
    on_losing=(
        "Concludes he was still not careful enough. Shrinks harder, widens "
        "further, raises his confidence floor and publishes even less."
    ),
    weakness=(
        "Says almost nothing. Perfectly calibrated and frequently useless, "
        "because a prediction indistinguishable from the average is not a "
        "prediction."
    ),
    edge="Never blowing up. When the others are wrong together, Tayler is not.",
)

BDOG = Character(
    id="bdog",
    name="Bdog",
    emotion="Bravery",
    tagline="If everyone agrees, someone is not looking.",
    philosophy=(
        "Bravery is willing to be alone. Bdog computes what the other four "
        "believe and deliberately shades away from it, on the argument that "
        "consensus is where the value has already gone. He trusts thin evidence "
        "the others shrink away, because someone has to be first."
    ),
    on_losing=(
        "Notes that being early looks identical to being wrong, and holds the "
        "position. Only capitulates on sustained evidence, not on one bad week."
    ),
    weakness=(
        "Contrarian by construction. When the consensus is simply correct, "
        "which is most of the time, Bdog is systematically off."
    ),
    edge="Overreaction. Fixtures the crowd has collectively mispriced.",
)

ALL: tuple[Character, ...] = (ALAN, LILY, VALENTINA, TAYLER, BDOG)
BY_ID: dict[str, Character] = {c.id: c for c in ALL}


def get(character_id: str) -> Character:
    if character_id not in BY_ID:
        raise KeyError(f"unknown character {character_id!r}. Known: {sorted(BY_ID)}")
    return BY_ID[character_id]
