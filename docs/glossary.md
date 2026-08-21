# Glossary

Terms used precisely in this repository, especially the ones that are ambiguous elsewhere.

**as_of** — The timestamp a feature set is built for. Only facts with `known_at <= as_of` may be used. The mechanism that prevents look-ahead.

**Backtest** — Walk-forward evaluation across historical matchweeks under strict point-in-time rules. Not a simulation of past profits, an evaluation of predictive quality.

**Brier score** — Mean squared error of a probabilistic forecast against a binary outcome. Lower is better.

**Calibration** — Whether predicted probabilities match observed frequencies. If everything we call 30% happens 30% of the time, we are calibrated. Calibration is necessary; on its own it is not sufficient, since always predicting the base rate is perfectly calibrated and useless.

**Challenger** — A registered model that is not currently champion. Runs alongside, scored identically, not shown as the site's headline prediction.

**Champion** — The model currently promoted for a given market. Its predictions are the ones the site presents by default.

**Closing line value (CLV)** — The difference between the price available when a prediction was made and the market's closing price. The fastest reliable evidence of edge.

**Conformal prediction** — A method for producing uncertainty intervals with guaranteed coverage under weak assumptions. Candidate for honest uncertainty bands on the site.

**CRPS** — Continuous ranked probability score. Scores an entire predicted distribution against a realised value rather than scoring one threshold. The right metric for count markets.

**Distribution family** — Whether a market is modelled as a `count` (fouls, tackles) or as `binary` (cards). Declared per market, because modelling a near-binary outcome as a count wastes model capacity.

**Dixon-Coles** — The 1997 approach to football modelling using team attack and defence ratings with exponential time decay. Still the backbone of serious football rating systems. We borrow the ratings machinery, not the goals model.

**Entity** — The thing a prediction is about: a player, a team or a match.

**Fair odds** — The decimal price implied by our model's probability, with no margin. `1 / p`. What we publish. Not a bookmaker price.

**Fouls committed vs fouls drawn** — Committed means the player gave the foul away. Drawn (also "fouled") means the foul was against him. The 2025 model combined the two into "foul involvements", which is not a market anyone offers.

**known_at** — The earliest moment a fact was knowable from public information. Stored on every fact row. The other half of the leakage defence.

**Leakage** — Using information in a prediction that was not available at prediction time. The failure that invalidated the 2025 version's evaluation.

**Line** — The threshold a market settles against, for example 1.5 fouls. Bets settle over or under. Half-lines exist so there is no push.

**Market** — Here, a thing we predict (player fouls committed). Not a bookmaker's trading market. When the bookmaker sense is meant, it is written as "bookmaker market".

**Market baseline** — A pseudo-model that converts bookmaker prices to probabilities with margin removed. The real bar to beat.

**Overdispersion** — Variance exceeding the mean, which breaks the Poisson assumption. Common in foul counts. Handled with negative binomial models.

**Partial pooling** — Estimating group effects (players, referees) jointly so small samples get pulled toward the group mean in proportion to their uncertainty. The principled version of what the 2025 model attempted with hand-tuned multipliers.

**Point-in-time correctness** — The property that every input to a prediction was knowable before the prediction moment. See `as_of` and `known_at`.

**Post-lineup / pre-lineup** — Whether a prediction was made before or after official lineups were published, roughly an hour before kickoff. Scored separately, always.

**Shrinkage** — Pulling a noisy individual estimate toward a group average, more strongly when the individual sample is smaller.

**Snapshot** — A frozen parquet dump of the database used for reproducible experiments. Identified by a content hash.

**Vig / margin / overround** — The bookmaker's built-in edge, which makes quoted probabilities sum to more than 100%. Must be removed before comparing a bookmaker price to a model probability.
