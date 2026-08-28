"""A confirmed eleven always draws a pitch.

On 28 August 2026 the league posted Palace v City's elevens with no formation
block, the shaper produced no lines, the publisher emitted no shape for the
fixture at all, and the pitch vanished from the page the moment the lineups
were confirmed. When the league does not say the shape, the eleven is drawn
by position, goalkeeper first, and the header says "by position"."""

from foulgorithm.sources import lineups


def entry(name, pos, pid):
    return {"id": pid, "name": {"display": name}, "matchPosition": pos, "matchShirtNumber": pid}


def detail(formation):
    eleven = (
        [entry("Keeper", "G", 1)]
        + [entry(f"D{i}", "D", 10 + i) for i in range(4)]
        + [entry(f"M{i}", "M", 20 + i) for i in range(3)]
        + [entry(f"F{i}", "F", 30 + i) for i in range(3)]
    )
    return {
        "teams": [
            {"team": {"id": 6, "name": "Crystal Palace"}},
            {"team": {"id": 11, "name": "Manchester City"}},
        ],
        "teamLists": [
            {"teamId": 6, "formation": formation, "lineup": eleven, "substitutes": []},
            None,
        ],
    }


class TestShapeWithoutAFormation:
    def test_the_eleven_is_grouped_by_position_keeper_first(self):
        out = lineups.shape_detail(detail(None), "Crystal Palace v Man City")
        lu = out["Crystal Palace|Crystal Palace v Man City"]
        assert lu.formation is None
        assert [len(line) for line in lu.lines] == [1, 4, 3, 3]
        assert lu.lines[0][0].name == "Keeper"

    def test_a_published_formation_is_still_used_as_given(self):
        formation = {
            "label": "3-4-3",
            "players": [[1], [10, 11, 12], [13, 20, 21, 22], [30, 31, 32]],
        }
        out = lineups.shape_detail(detail(formation), "Crystal Palace v Man City")
        lu = out["Crystal Palace|Crystal Palace v Man City"]
        assert lu.formation == "3-4-3"
        assert [len(line) for line in lu.lines] == [1, 3, 4, 3]
