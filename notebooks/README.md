# Notebooks

Exploration only.

## The rule

**Notebooks contain no logic.** They import from `foulgorithm`, call it and display the results. Anything worth keeping moves into the package with a test.

This rule exists because the 2025 version's real logic lived across two notebooks and a script with overlapping, drifting copies of the same calculations. Nobody could say which version produced a given output.

## What belongs here

- Looking at a distribution to decide whether a market is a count or binary
- Checking whether a feature has any signal before writing it properly
- Producing a chart for a doc or the site
- Poking at a bad prediction to work out what happened

## What does not

- Any function another notebook would want
- Anything that runs in a scheduled job
- Anything whose output gets published

## Conventions

- Name them `NN-topic.ipynb`, for example `01-foul-distribution-shape.ipynb`.
- Read from a snapshot in `data/snapshots/`, never from the live database. Reproducible, and it will not be slow.
- Clear outputs before committing. Committed outputs make diffs unreadable and can leak keys.
- A notebook that has not been opened in three months is deleted, not maintained.
