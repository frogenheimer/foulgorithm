"""Match current squad players to their history.

FPL publishes legal names ("David Raya Martín", "Mikel Merino Zazón"). Our
history carries common names ("David Raya", "Mikel Merino"). Matching them is
the join that makes current squads useful, and it is also the join most likely
to be wrong in a way nobody notices.

A naive surname match produces confident nonsense. Tested on real data it paired
"Will Dennis" with "Emmanuel Dennis" and "Mamadou Sangaré" with "Ibrahim
Sangaré": different people, same surname, and a foul rate transplanted between
them. Surname matching is therefore not used at all.

What is used, in order:

  1. Exact match on the normalised full name.
  2. Token subset: every word of the history name appears in the FPL name, and
     exactly one history name qualifies.

Rule 2 catches the legal-name case ("gabriel magalhaes" sits inside "gabriel dos
santos magalhaes") while refusing anything ambiguous. Where more than one
candidate qualifies, the player is left UNMATCHED on purpose.

Unmatched is a safe outcome, not a failure: that player falls back to the prior
for his position, and the site says his evidence is thin. Wrong is not safe.
See docs/decisions/ADR-007-identity-halts-pipeline.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from foulgorithm.sources.fpl import SquadPlayer, normalise

CROSSWALK = Path("data/reference/crosswalk_players.yaml")


@dataclass(frozen=True)
class Resolution:
    matched: dict[str, str]  # FPL full name -> history name
    unmatched: list[str]  # FPL full names with no safe match
    ambiguous: dict[str, list[str]]  # FPL full name -> the candidates we refused


def build_index(history_names) -> dict[str, str]:
    index: dict[str, str] = {}
    for name in history_names:
        index.setdefault(normalise(str(name)), str(name))
    return index


def load_overrides(path: Path = CROSSWALK) -> dict[str, str]:
    """Human-confirmed matches, checked into git and reviewable in a diff.

    The automatic rules refuse anything ambiguous, which is correct and also
    leaves real players unresolved. A person settles those here, once.
    """
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    return {normalise(k): v for k, v in (data.get("aliases") or {}).items()}


def resolve_names(names, history_names, overrides: dict | None = None) -> Resolution:
    """Resolve plain name lists, with the token rule running both ways.

    `resolve` checks one direction: every word of the history name appears in
    the source name, which is the FPL case, where legal names are longer.
    Provider joins face both cases: the league API abbreviates ("Abdul
    Fatawu" for the archive's "Abdul Fatawu Issahaku") as often as FPL
    lengthens. The refusal rules are unchanged in both directions: two
    candidates is a refusal, and a lone token never matches anything, because
    surname matching once transplanted a foul rate between two different
    players called Dennis.
    """
    index = build_index(history_names)
    overrides = load_overrides() if overrides is None else overrides
    token_index: dict[frozenset[str], list[str]] = {}
    for key, original in index.items():
        token_index.setdefault(frozenset(key.split()), []).append(original)

    matched: dict[str, str] = {}
    unmatched: list[str] = []
    ambiguous: dict[str, list[str]] = {}

    for name in names:
        key = normalise(str(name))
        if key in overrides:
            matched[name] = overrides[key]
            continue
        if key in index:
            matched[name] = index[key]
            continue

        tokens = frozenset(key.split())
        candidates = set()
        for hist_tokens, originals in token_index.items():
            forward = len(hist_tokens) >= 2 and hist_tokens <= tokens
            reverse = len(tokens) >= 2 and tokens <= hist_tokens
            if forward or reverse:
                candidates.add(originals[0])

        ordered = sorted(candidates)
        if len(ordered) == 1:
            matched[name] = ordered[0]
        elif ordered:
            ambiguous[name] = ordered
            unmatched.append(name)
        else:
            unmatched.append(name)

    return Resolution(matched=matched, unmatched=unmatched, ambiguous=ambiguous)


def resolve(players: list[SquadPlayer], history_names, overrides: dict | None = None) -> Resolution:
    index = build_index(history_names)
    overrides = load_overrides() if overrides is None else overrides
    token_index: dict[frozenset[str], list[str]] = {}
    for key, original in index.items():
        token_index.setdefault(frozenset(key.split()), []).append(original)

    matched: dict[str, str] = {}
    unmatched: list[str] = []
    ambiguous: dict[str, list[str]] = {}

    for player in players:
        key = player.key
        if key in overrides:
            matched[player.name] = overrides[key]
            continue
        if key in index:
            matched[player.name] = index[key]
            continue

        tokens = set(key.split())
        # Every word of the history name must appear in the FPL name. Require at
        # least two words so a lone surname can never resolve on its own.
        candidates = [
            names[0]
            for hist_tokens, names in token_index.items()
            if len(hist_tokens) >= 2 and hist_tokens <= tokens
        ]
        candidates = sorted(set(candidates))

        if len(candidates) == 1:
            matched[player.name] = candidates[0]
        elif len(candidates) > 1:
            ambiguous[player.name] = candidates
            unmatched.append(player.name)
        else:
            unmatched.append(player.name)

    return Resolution(matched=matched, unmatched=unmatched, ambiguous=ambiguous)
