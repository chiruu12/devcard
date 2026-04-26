from __future__ import annotations

import json
from datetime import UTC, datetime

from devcard.models import Activity, DevCard, Generator, Identity, Language
from devcard.output.toon_output import to_toon


def _make_devcard(**overrides) -> DevCard:
    defaults = dict(
        generated_at=datetime.now(UTC),
        generator=Generator(name="devcard", version="0.1.0"),
        identity=Identity(username="testuser", name="Test User", bio="I build things"),
    )
    defaults.update(overrides)
    return DevCard(**defaults)


class TestToonOutput:
    def test_output_is_nonempty_string(self):
        result = to_toon(_make_devcard())
        assert isinstance(result, str)
        assert len(result) > 0

    def test_output_contains_username(self):
        result = to_toon(_make_devcard())
        assert "testuser" in result

    def test_output_smaller_than_json(self):
        dc = _make_devcard(
            languages=[
                Language(name="Python", percentage=60.0, color="#3572A5", bytes=1000000),
                Language(name="TypeScript", percentage=25.0, color="#3178c6", bytes=500000),
                Language(name="Go", percentage=15.0, color="#00ADD8", bytes=200000),
            ],
            activity=Activity(
                status="active",
                commits_last_year=500,
                peak_hours=[10, 14, 16],
            ),
        )
        toon_size = len(to_toon(dc))
        json_size = len(json.dumps(dc.model_dump(exclude_none=True, mode="json"), indent=2))
        assert toon_size < json_size

    def test_minimal_devcard(self):
        dc = DevCard(
            generated_at=datetime.now(UTC),
            generator=Generator(name="devcard", version="0.1.0"),
            identity=Identity(username="minuser"),
        )
        result = to_toon(dc)
        assert isinstance(result, str)
        assert "minuser" in result

    def test_output_contains_languages(self):
        dc = _make_devcard(
            languages=[
                Language(name="Rust", percentage=45.0),
                Language(name="Haskell", percentage=30.0),
                Language(name="Elixir", percentage=25.0),
            ],
        )
        result = to_toon(dc)
        assert "Rust" in result
        assert "Haskell" in result
        assert "Elixir" in result
