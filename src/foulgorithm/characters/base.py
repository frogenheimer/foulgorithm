"""The competitors: the five, and the 6~7 who joined to beat them.

Each character is a research philosophy with a temperament attached, not a
handicap. Every one is a position a real analyst could defend, which is what
makes the competition worth running: any of them could win. Generation 1
(the five) bets on pure temperament; generation 2 (the challengers) bets
under the bounded rules in docs/38, and the league is the experiment.

The rule that matters: a character may be wrong, but a character may never
be deliberately stupid.
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
    #: Which selection rules the character bets under. Generation 1 is pure
    #: temperament; generation 2 is bounded temperament with a guaranteed hot
    #: take (docs/38). The league runs both side by side, which is the test.
    generation: int = 1


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

PAX = Character(
    id="pax",
    name="Pax",
    emotion="Persistence",
    tagline="Form is loud. Habit is true.",
    philosophy=(
        "Persistence believes people are what they repeatedly do. Pax keeps a "
        "long memory, demands a body of evidence before trusting a number, and "
        "is unmoved by a hot fortnight in either direction. He backs the "
        "players who foul every week because they have always fouled every "
        "week, and he is suspicious of any story that requires the word "
        "'suddenly'."
    ),
    on_losing=(
        "Changes nothing, on principle. A bad week is exactly what variance is "
        "supposed to look like, and reacting to it would be the mistake."
    ),
    weakness=(
        "Slow to everything. A genuine change, a new role, a new manager, a "
        "lost yard of pace, takes Pax months to believe."
    ),
    edge="Stability. The bankers everyone else talks themselves out of.",
    generation=2,
)

JUSTINE = Character(
    id="justine",
    name="Justine",
    emotion="Jealousy",
    tagline="Whatever the leader has, she wants.",
    philosophy=(
        "Jealousy studies the winner. Justine reads the league table before "
        "she reads the fixtures, and inside the close calls she leans toward "
        "whatever the current leader's numbers say, on the argument that "
        "success is evidence. When the table has no leader yet she covets the "
        "consensus instead, which is the same instinct pointed at the crowd."
    ),
    on_losing=(
        "Concludes she copied the wrong rival and switches allegiance to "
        "whoever has just overtaken them."
    ),
    weakness=(
        "Always one step behind. She inherits the leader's mistakes at "
        "exactly the moment the leader starts making them."
    ),
    edge="Free-riding on whoever is genuinely in form, without their blind spots.",
    generation=2,
)

MABEL = Character(
    id="mabel",
    name="Mabel",
    emotion="Madness",
    tagline="The chaos is the signal.",
    philosophy=(
        "Madness trusts what just happened and nothing else. Mabel runs a "
        "short memory, barely shrinks, and is drawn to exactly the players "
        "the others smooth away: the erratic ones, the thin samples, the "
        "numbers still moving. Where the field sees noise she sees a player "
        "mid-transformation, and she would rather be early and wrong than "
        "late and right."
    ),
    on_losing=(
        "Delighted. A loss proves the world is as unstable as she said, and "
        "she doubles her appetite for the volatile."
    ),
    weakness=(
        "Most of the chaos is just chaos. Mabel pays the variance tax weekly and calls it tuition."
    ),
    edge="Genuine breakouts, role changes and new signings, caught first.",
    generation=2,
)

DOTTIE = Character(
    id="dottie",
    name="Dottie",
    emotion="Deviance",
    tagline="The obvious pick is priced. The odd one is free.",
    philosophy=(
        "Deviance is disagreement with a method. Dottie takes the pack's view "
        "as her starting point and looks for the places her own numbers "
        "genuinely part company with it, then leans that way inside the close "
        "calls. Unlike Bravery, she never manufactures a disagreement: she "
        "amplifies the real ones."
    ),
    on_losing=(
        "Checks whether the disagreement was hers or the data's. If it was "
        "genuinely hers, she keeps it; a position abandoned on one loss was "
        "never a position."
    ),
    weakness=(
        "Her edge cases are by definition the thinnest evidence on the "
        "board, and a hot take pays a cold price more often than not."
    ),
    edge="The mispriced middle: players the pack has quietly stopped watching.",
    generation=2,
)

DELE = Character(
    id="dele",
    name="Dele",
    emotion="Delinquency",
    tagline="Backs the players referees already know by name.",
    philosophy=(
        "Delinquency respects a record. Dele reads raw foul rates the way "
        "others read form: a player who commits, and keeps committing, is "
        "his kind of player, whatever the matchup says. He keeps a long "
        "memory for repeat offenders and shrugs at context, because the "
        "career recidivist does not need a reason."
    ),
    on_losing=("Blames the referee for going soft and backs the same names again, harder."),
    weakness=(
        "Reputation outlives behaviour. A reformed midfielder stays on "
        "Dele's list a season too long."
    ),
    edge="The persistent foulers whose rates survive every change of scenery.",
    generation=2,
)

IAN = Character(
    id="ian",
    name="magicIan",
    emotion="Intelligence",
    tagline="Whatever loses, he stops being.",
    philosophy=(
        "Intelligence here is a genetic algorithm, not a temperament. Every "
        "matchday magicIan reads the whole field's graded results, breeds a "
        "population of candidate settings from the winners, mutates them, "
        "and becomes whichever candidate scores best on what actually "
        "happened. His dials are different every week by construction, and "
        "his entire lineage is committed to the record, so his evolution can "
        "be audited like everything else."
    ),
    on_losing=(
        "Losing IS his method: a bad week is selection pressure, and the "
        "next generation is bred from whatever beat him."
    ),
    weakness=(
        "Overfits the recent past by design. Whatever worked last month is "
        "what he has evolved into, exactly in time for it to stop working."
    ),
    edge="Never married to an idea. The only competitor guaranteed to change.",
    generation=2,
)

ALL: tuple[Character, ...] = (
    ALAN,
    LILY,
    VALENTINA,
    TAYLER,
    BDOG,
    PAX,
    JUSTINE,
    MABEL,
    DOTTIE,
    DELE,
    IAN,
)
BY_ID: dict[str, Character] = {c.id: c for c in ALL}

#: Generation 2, the challengers: bounded temperament, guaranteed hot take.
V2_IDS: frozenset[str] = frozenset(c.id for c in ALL if c.generation == 2)


def get(character_id: str) -> Character:
    if character_id not in BY_ID:
        raise KeyError(f"unknown character {character_id!r}. Known: {sorted(BY_ID)}")
    return BY_ID[character_id]
