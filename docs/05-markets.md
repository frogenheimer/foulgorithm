# Markets

**Status: Proposed**

A market is the thing we predict. The point of this module is that adding a new one means adding a definition, not editing the model or the backtest.

## Definition

Each market is a `MarketSpec`:

| Field | Meaning |
|---|---|
| `key` | Stable identifier, for example `player_fouls_committed` |
| `label` | Human name for the site |
| `entity` | `player`, `team` or `match` |
| `family` | `count` or `binary`. Determines which distribution the model returns |
| `stat_column` | Which column in the fact tables holds the observed value |
| `lines` | The line grid we publish, for example 0.5, 1.5, 2.5, 3.5 |
| `settlement_note` | How bookmakers actually settle this, in plain words |
| `min_minutes` | Minutes threshold below which we do not publish for an entity |

## Launch markets

### `player_fouls_committed` (count)

The original market and the best understood. Counts are low (most players commit 0 to 3), overdispersed relative to Poisson, and strongly driven by position, minutes and opponent.

Settlement note: bookmakers settle on the official data provider's "fouls committed" figure. Handballs, offsides and advantage situations are treated inconsistently across providers. **This needs verifying against a specific provider before any value claim is made.** Tracked as an open question in [12-risks-and-open-questions.md](12-risks-and-open-questions.md).

### `player_fouls_drawn` (count)

Fouls committed **against** the player, listed by providers as "fouled" or "fouls won". A genuinely separate market from fouls committed, and driven by different traits: dribblers and forwards draw fouls, while defenders and holding midfielders commit them. A player can rank highly in one and near the bottom of the other.

**Never combine the two.** The 2025 version summed them into "foul involvements" and ranked players on it. No bookmaker prices that, so the ranking could not be bet even when it was right.

Settlement note: providers differ on whether a foul that leads to an advantage being played counts, and on penalties won. Verify against the settling provider.

### `player_tackles` (count)

Shares almost every feature with fouls and is closely related mechanically: tackles attempted is the strongest single predictor of fouls committed. Modelling both jointly is likely to help each.

Settlement note: providers differ on whether a tackle requires winning the ball. This materially changes the number.

### `player_cards` (binary)

**Not a count market, despite looking like one.** Second yellows and straight reds are rare enough that the useful question is "is this player booked at all", which is a Bernoulli outcome with probability typically between 5% and 25%.

Modelling this as a count would waste the model's capacity on a tail that almost never occurs. The `family` field exists precisely so this market gets treated correctly.

Settlement note: most books settle "to be booked" on a yellow or red at any point, including after the player is substituted, and typically exclude cards shown to non-playing staff or players on the bench. Post-match retrospective cards do not count.

## Derived market outputs

From one fitted distribution we publish every line for free:

- P(over each line) and P(under each line)
- Fair decimal odds, which is simply 1 divided by the probability
- The full probability mass function, which is what the site's interactive line explorer renders

There is no separate model per line. A model that predicts "over 1.5 fouls" directly, rather than predicting the distribution, cannot answer "over 2.5" without refitting, and its answers across lines can be mutually inconsistent.

## Team and match markets

`team_fouls_committed` and `match_total_fouls` come almost free once player-level distributions exist, by convolving the individual distributions with an adjustment for the fact that team fouls are not independent across players. They are lower priority than player markets because bookmakers price them more efficiently.

## Adding a market later

The intended sequence for anything new (shots, offsides, corners conceded):

1. Confirm the underlying stat exists in `player_match_stats` for the history we have.
2. Write the `MarketSpec`.
3. Confirm the distribution family fits by checking the empirical variance-to-mean ratio.
4. Run the existing baselines through the backtest harness for that market.
5. Only then consider whether a bespoke model is worth building.

Steps 1 to 4 should require no new modelling code at all. If they do, the abstraction is wrong and the abstraction gets fixed rather than worked around.
