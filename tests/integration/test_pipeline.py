import asyncio
from pathlib import Path
import pytest

from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.database.models import Business, PipelineRun
from app.database.repositories import (
    BusinessRepository,
    LeadScoreRepository,
    PipelineRunRepository,
)
from app.discovery.base import BaseDiscoveryProvider
from app.pipeline.runner import PipelineRunner


def test_sqlite_migrations_and_repositories(tmp_path):
    db_path = tmp_path / "test.db"
    conn = get_connection(db_path)
    try:
        applied = run_migrations(conn)
        assert applied == 1

        biz_repo = BusinessRepository(conn)
        b = Business(
            name="Hill Country BBQ",
            normalized_name="hill country bbq",
            vertical="restaurant",
            city="Austin",
            state="Texas",
            phone="512-555-8888",
            normalized_phone="+15125558888",
        )
        b_id = biz_repo.insert(b)
        assert b_id > 0

        fetched = biz_repo.get_by_id(b_id)
        assert fetched is not None
        assert fetched.name == "Hill Country BBQ"
        assert fetched.normalized_phone == "+15125558888"

        # Test pipeline run repo
        run_repo = PipelineRunRepository(conn)
        pr = PipelineRun(market="Austin, TX", vertical="restaurant", target=50)
        run_id = run_repo.create(pr)
        assert run_id > 0

        fetched_run = run_repo.get_by_id(run_id)
        assert fetched_run.market == "Austin, TX"
    finally:
        conn.close()


class MockDiscoveryProvider(BaseDiscoveryProvider):
    @property
    def name(self) -> str:
        return "Mock Discovery"

    def search(self, market, vertical, limit=50):
        return [
            Business(
                name="Austin Craft Coffee",
                normalized_name="austin craft coffee",
                vertical="restaurant",
                city="Austin",
                state="Texas",
                country="United States",
                phone="512-555-2233",
                normalized_phone="+15125552233",
                website="https://austincraftcoffee.example",
                domain="austincraftcoffee.example",
                source_overture=True,
                source_confidence=0.9,
            ),
            Business(
                name="Chipotle Mexican Grill",  # Should be flagged as chain
                normalized_name="chipotle mexican grill",
                vertical="restaurant",
                city="Austin",
                state="Texas",
                country="United States",
                website="https://www.chipotle.com",
                domain="chipotle.com",
                source_osm=True,
                source_confidence=0.9,
            ),
            Business(
                name="Tacos No-Web",
                normalized_name="tacos no web",
                vertical="restaurant",
                city="Austin",
                state="Texas",
                country="United States",
                phone="512-555-4455",
                normalized_phone="+15125554455",
                website=None,
                source_osm=True,
                source_confidence=0.8,
            ),
        ]


@pytest.mark.asyncio
async def test_pipeline_integration(monkeypatch, tmp_path):
    # Mock discovery providers to be deterministic and fast
    mock_prov = MockDiscoveryProvider()
    from app.config.markets import resolve_market
    market_info = resolve_market("Austin, Texas, USA")

    monkeypatch.setattr("app.pipeline.runner.DiscoveryCoordinator.discover",
        lambda self, market_str, vertical_str, target_leads, include_chains: (
            market_info,
            type("Vert", (), {"key": "restaurant", "display_name": "Restaurants"}),
            [mock_prov.search(None, None)[0], mock_prov.search(None, None)[2]], # Candidates (excluding chain)
            [mock_prov.search(None, None)[1]], # Rejected chain
        )
    )

    test_db = tmp_path / "test_pipeline.db"
    test_out = tmp_path / "output"
    runner = PipelineRunner(db_path=test_db, output_dir=test_out)
    run = await runner.run(
        market="Austin, Texas, USA",
        vertical="restaurant",
        target=10,
        enable_lighthouse=False,
    )

    assert run.status == "COMPLETED"
    assert run.qualified >= 1
    assert run.output_file is not None
    assert Path(run.output_file).exists()
