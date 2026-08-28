"""magicIan: a genetic algorithm competing in the league. See docs/38.

Every matchday, after settle grades the round, Ian breeds a population from
his current dials, every rival's dial set (learning from the others is the
point: their graded weaknesses are exactly what the evaluation exposes),
and mutants and crossovers of both. Each candidate is scored walk-forward
on recent player-matches, fitting only on what was known before each batch,
and the best genome becomes Ian for the next round.

Three structural rules keep this fair. The lineage is append-only, so his
evolution is as auditable as anyone's picks. Every gene lives inside named
bounds, so he can never mutate into something no analyst could defend.
And generation N always breeds the same candidates, so a re-run cannot
quietly produce a different Ian.
"""

from __future__ import annotations

import json
import random
from datetime import UTC
from pathlib import Path

LINEAGE = Path("data/state/magician_lineage.jsonl")

#: The dials and how far they may wander. Same genes as every other
#: character's configuration; the bounds cover the whole range the five and
#: the challengers occupy, with a little room either side.
GENE_BOUNDS: dict[str, tuple[float, float]] = {
    "half_life_days": (60, 1500),
    "prior_matches": (1, 40),
    "opponent_weight": (0.3, 1.8),
    "dispersion": (0.9, 1.35),
    "amplify": (0.9, 1.45),
}

#: Where Ian starts before his first generation: deliberately unopinionated.
SEED: dict[str, float] = dict(
    half_life_days=500, prior_matches=8, opponent_weight=1.0, dispersion=1.10, amplify=1.10
)

POPULATION = 16
#: How far back the fitness evaluation looks, in days of player-matches.
EVAL_WINDOW_DAYS = 120


def current_genome(path: Path = LINEAGE) -> dict:
    """Ian's dials now: the last generation's winner, or the seed."""
    rows = lineage(path)
    return dict(rows[-1]["settings"]) if rows else dict(SEED)


def lineage(path: Path = LINEAGE) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def clamp(genome: dict) -> dict:
    out = {}
    for gene, (lo, hi) in GENE_BOUNDS.items():
        value = float(genome.get(gene, SEED[gene]))
        out[gene] = min(max(value, lo), hi)
    out["prior_matches"] = round(out["prior_matches"], 1)
    out["half_life_days"] = round(out["half_life_days"])
    for gene in ("opponent_weight", "dispersion", "amplify"):
        out[gene] = round(out[gene], 3)
    return out


def mutate(genome: dict, rng: random.Random, scale: float = 0.25) -> dict:
    """Gaussian noise on every gene, proportional to its allowed range."""
    child = {}
    for gene, (lo, hi) in GENE_BOUNDS.items():
        span = hi - lo
        child[gene] = float(genome.get(gene, SEED[gene])) + rng.gauss(0, span * scale / 3)
    return clamp(child)


def crossover(a: dict, b: dict, rng: random.Random) -> dict:
    """Each gene from one parent or the other, coin per gene."""
    return clamp(
        {gene: (a if rng.random() < 0.5 else b).get(gene, SEED[gene]) for gene in GENE_BOUNDS}
    )


def _rival_settings() -> dict[str, dict]:
    from foulgorithm.models import player_models as pm

    out = {}
    for cid, settings in pm.CHARACTER_SETTINGS.items():
        if cid == "ian":
            continue
        out[cid] = {gene: settings[gene] for gene in GENE_BOUNDS if gene in settings}
    return out


def _population(champion: dict, generation: int) -> list[dict]:
    """The candidates for one generation, deterministic per generation."""
    rng = random.Random(generation * 9973)
    rivals = _rival_settings()

    candidates = [{"origin": "champion", "settings": clamp(champion)}]
    for cid in sorted(rivals):
        candidates.append({"origin": f"rival:{cid}", "settings": clamp(rivals[cid])})

    pool = [c["settings"] for c in candidates]
    while len(candidates) < POPULATION:
        if rng.random() < 0.5:
            a, b = rng.sample(pool, 2)
            candidates.append({"origin": "crossover", "settings": crossover(a, b, rng)})
        else:
            candidates.append({"origin": "mutant", "settings": mutate(rng.choice(pool), rng)})
    return candidates


def evaluate(genome: dict, history=None, window_days: int = EVAL_WINDOW_DAYS) -> float | None:
    """Mean log loss for one genome, walk-forward over recent player-matches.

    Weekly batches, fitting only on rows known before each batch, exactly as
    the backtest harness works: the score is what this genome WOULD have
    said, never what it says now about then. None when there is not enough
    data to score honestly, and an unscorable candidate never wins.
    """
    import pandas as pd

    from foulgorithm.backtest import metrics as mx
    from foulgorithm.models import player_models as pm

    if history is None:
        from foulgorithm.store.players import load_player_matches

        history = load_player_matches()

    history = history.sort_values("kickoff_utc").reset_index(drop=True)
    cutoff = history["kickoff_utc"].max() - pd.Timedelta(days=window_days)
    evaluation = history[history["kickoff_utc"] >= cutoff]
    if evaluation.empty:
        return None

    week = (evaluation["kickoff_utc"] - evaluation["kickoff_utc"].min()).dt.days // 7
    model = pm.PlayerFoulModel(character_id="ian", **genome)

    # The same arithmetic as backtest/player_harness.py, scored on actual
    # minutes so this measures the foul dials rather than the minutes model.
    losses: list[float] = []
    for _, batch in evaluation.groupby(week):
        as_of = batch["kickoff_utc"].min()
        train = history[history["known_at"] <= as_of]
        if len(train) < 20000:
            continue
        model.fit(train)
        for row in batch.itertuples():
            rate, _ = model.player_rate(row.player, as_of)
            opp = model.opponent_factor(row.opponent, as_of)
            mean = max(rate * (row.minutes / 90.0) * opp, 0.02)
            dist = pm.negbin_pmf(mean, mean * max(model.dispersion, 1.02))
            observed = float(row.fouls_committed)
            for line in (0.5, 1.5):
                losses.append(mx.log_loss_at_line(dist, observed, line))
    return sum(losses) / len(losses) if losses else None


def step(
    history=None,
    path: Path = LINEAGE,
    evaluate_fn=None,
    window_days: int = EVAL_WINDOW_DAYS,
) -> dict:
    """Breed, score and crown one generation. Appends to the lineage."""
    from datetime import datetime

    rows = lineage(path)
    generation = len(rows) + 1
    champion = dict(rows[-1]["settings"]) if rows else dict(SEED)
    scorer = evaluate_fn or (
        lambda genome, **kw: evaluate(genome, history=history, window_days=window_days)
    )

    candidates = _population(champion, generation)
    for candidate in candidates:
        candidate["fitness"] = scorer(candidate["settings"])

    scored = [c for c in candidates if c["fitness"] is not None]
    if not scored:
        winner = {"origin": "champion", "settings": clamp(champion), "fitness": None}
    else:
        winner = min(scored, key=lambda c: c["fitness"])

    row = {
        "generation": generation,
        "settings": winner["settings"],
        "origin": winner["origin"],
        "fitness": winner["fitness"],
        "population": candidates,
        "evolvedAt": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(row) + "\n")
    return row
