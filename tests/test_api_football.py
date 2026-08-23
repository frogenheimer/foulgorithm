"""The API-Football client, tested without spending requests.

The free plan meters requests hard, so nothing here touches the network. What
matters is the shape: a missing key must raise rather than return empty, and an
error delivered with a 200 must not be mistaken for success.
"""

import pytest

from foulgorithm.sources import api_football
from foulgorithm.sources.base import SourceError


class TestTheKey:
    def test_a_missing_key_raises_rather_than_returning_nothing(self, monkeypatch, tmp_path):
        """A source that silently returns nothing looks like a quiet week."""
        monkeypatch.setenv("API_FOOTBALL_KEY", "")
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SourceError, match="API_FOOTBALL_KEY"):
            api_football._key()

    def test_the_environment_wins(self, monkeypatch):
        monkeypatch.setenv("API_FOOTBALL_KEY", "from-env")
        assert api_football._key() == "from-env"

    def test_it_falls_back_to_the_env_file(self, monkeypatch, tmp_path):
        monkeypatch.delenv("API_FOOTBALL_KEY", raising=False)
        (tmp_path / ".env").write_text('API_FOOTBALL_KEY="from-file"\n')
        monkeypatch.chdir(tmp_path)
        assert api_football._key() == "from-file"


class TestErrorsArriveAsSuccess:
    """The API answers 200 with an errors object, so a plan or quota problem
    looks exactly like a good response until you check."""

    def test_an_errors_object_raises(self, monkeypatch):
        monkeypatch.setenv("API_FOOTBALL_KEY", "x")
        monkeypatch.setattr(
            api_football.urllib.request,
            "urlopen",
            lambda *a, **k: _FakeResponse({"errors": {"plan": "upgrade required"}}),
        )
        with pytest.raises(SourceError, match="upgrade required"):
            api_football._get("status")

    def test_an_empty_errors_object_is_fine(self, monkeypatch):
        monkeypatch.setenv("API_FOOTBALL_KEY", "x")
        monkeypatch.setattr(
            api_football.urllib.request,
            "urlopen",
            lambda *a, **k: _FakeResponse({"errors": [], "response": [1, 2]}),
        )
        assert api_football._get("status")["response"] == [1, 2]


class TestShapingPlayerRows:
    def test_fouls_come_out_per_player(self, monkeypatch):
        monkeypatch.setenv("API_FOOTBALL_KEY", "x")
        payload = {
            "errors": [],
            "response": [
                {
                    "team": {"name": "Liverpool"},
                    "players": [
                        {
                            "player": {"name": "Ryan Gravenberch"},
                            "statistics": [
                                {
                                    "games": {"minutes": 90, "position": "M"},
                                    "fouls": {"committed": 3, "drawn": 1},
                                    "cards": {"yellow": 1, "red": 0},
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        monkeypatch.setattr(
            api_football.urllib.request, "urlopen", lambda *a, **k: _FakeResponse(payload)
        )
        rows = api_football.player_fouls(1)
        assert rows == [
            {
                "player": "Ryan Gravenberch",
                "team": "Liverpool",
                "minutes": 90,
                "position": "M",
                "fouls_committed": 3,
                "fouls_drawn": 1,
                "yellows": 1,
                "reds": 0,
                "source": "api-football",
            }
        ]

    def test_a_player_with_no_statistics_is_skipped_not_zeroed(self, monkeypatch):
        monkeypatch.setenv("API_FOOTBALL_KEY", "x")
        payload = {
            "errors": [],
            "response": [
                {"team": {"name": "X"}, "players": [{"player": {"name": "A"}, "statistics": []}]}
            ],
        }
        monkeypatch.setattr(
            api_football.urllib.request, "urlopen", lambda *a, **k: _FakeResponse(payload)
        )
        assert api_football.player_fouls(1) == []


class _FakeResponse:
    def __init__(self, payload):
        import json

        self._body = json.dumps(payload).encode()
        self.status = 200

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class TestADuplicatedName:
    """A .env that declares a name twice is normal after a copy-paste from
    .env.example, and reading the first match found the empty placeholder while
    a working key sat further down the file."""

    def test_the_last_non_empty_value_wins(self, monkeypatch, tmp_path):
        monkeypatch.delenv("API_FOOTBALL_KEY", raising=False)
        (tmp_path / ".env").write_text(
            "API_FOOTBALL_KEY=\nOTHER=1\nAPI_FOOTBALL_KEY=the-real-one\n"
        )
        monkeypatch.chdir(tmp_path)
        assert api_football._key() == "the-real-one"

    def test_an_empty_later_value_does_not_erase_an_earlier_one(self, monkeypatch, tmp_path):
        monkeypatch.delenv("API_FOOTBALL_KEY", raising=False)
        (tmp_path / ".env").write_text("API_FOOTBALL_KEY=good\nAPI_FOOTBALL_KEY=\n")
        monkeypatch.chdir(tmp_path)
        assert api_football._key() == "good"

    def test_all_empty_still_raises(self, monkeypatch, tmp_path):
        monkeypatch.delenv("API_FOOTBALL_KEY", raising=False)
        (tmp_path / ".env").write_text("API_FOOTBALL_KEY=\nAPI_FOOTBALL_KEY=\n")
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SourceError):
            api_football._key()
