#!/usr/bin/env python3
"""Export golden NFO fixtures from scraper.py and metadata-generator for Swift parity tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = (
    REPO_ROOT
    / "Native macOS App"
    / "Packages"
    / "PlexNFOCore"
    / "Tests"
    / "PlexNFOCoreTests"
    / "Fixtures"
)

sys.path.insert(0, str(REPO_ROOT))

from xml.etree.ElementTree import Element, SubElement  # noqa: E402

import scraper  # noqa: E402


def build_sample_movie() -> str:
    root = Element("movie")
    SubElement(root, "title").text = "Inception"
    SubElement(root, "year").text = "2010"
    scraper._uid(root, "tmdb", "27205", default=True)
    return scraper.pretty_xml(root)


def export_metadata_generator_fixtures() -> None:
    sys.path.insert(0, str(REPO_ROOT / "metadata-generator"))
    from plex_metadata_generator import (  # noqa: E402
        EpisodeMetadata,
        MovieMetadata,
        PlexNFOGenerator,
        ShowMetadata,
    )

    generator = PlexNFOGenerator()
    show = ShowMetadata(
        title="Fixture Show",
        year=2020,
        plot="Fixture plot",
        rating=8.5,
        tvdb_id=80348,
        tmdb_id=1396,
        imdb_id="tt0903747",
        genres=["Drama", "Crime"],
    )
    episode = EpisodeMetadata(
        title="Pilot",
        season=1,
        episode=1,
        plot="Episode plot",
        air_date="2008-01-20",
        rating=9.0,
        director="Director Name",
        writer="Writer Name",
    )
    movie = MovieMetadata(
        title="Fixture Movie",
        year=2010,
        plot="Movie plot",
        rating=8.8,
        runtime=148,
        genres=["Action"],
        tmdb_id=27205,
        imdb_id="tt1375666",
    )

    (FIXTURES_DIR / "mg-tvshow.nfo").write_text(generator.generate_show_nfo(show), encoding="utf-8")
    (FIXTURES_DIR / "mg-episode.nfo").write_text(generator.generate_episode_nfo(episode), encoding="utf-8")
    (FIXTURES_DIR / "mg-movie.nfo").write_text(generator.generate_movie_nfo(movie), encoding="utf-8")
    (FIXTURES_DIR / "mg-tvshow.json").write_text(
        json.dumps({"title": show.title, "year": show.year, "tvdb_id": show.tvdb_id, "tmdb_id": show.tmdb_id}, indent=2)
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    nfo_path = FIXTURES_DIR / "sample-movie.nfo"
    json_path = FIXTURES_DIR / "sample-movie.json"
    nfo_path.write_text(build_sample_movie(), encoding="utf-8")
    json_path.write_text(
        json.dumps({"title": "Inception", "year": "2010", "tmdb_id": "27205"}, indent=2) + "\n",
        encoding="utf-8",
    )
    export_metadata_generator_fixtures()
    print(f"Wrote scraper + metadata-generator fixtures to {FIXTURES_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
