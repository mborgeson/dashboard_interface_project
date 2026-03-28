"""
Tests for the StageChangeLog audit trail and unified stage mapping.

Covers:
- resolve_stage() path-component matching
- StageChangeLog creation for each source type
- stage_updated_at is always set when stage changes
- GET /api/v1/deals/{deal_id}/stage-history endpoint
- PATCH /{deal_id}/stage creates audit logs via Kanban
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deal import Deal, DealStage
from app.models.stage_change_log import StageChangeLog, StageChangeSource
from app.services.stage_mapping import (
    FOLDER_TO_STAGE,
    STAGE_ALIASES,
    STAGE_FOLDER_MAP,
    STAGE_TO_FOLDER,
    change_deal_stage,
    change_deal_stage_sync,
    resolve_stage,
)

# ── resolve_stage() tests ──────────────────────────────────────────────────


class TestResolveStage:
    """Tests for the canonical resolve_stage() function."""

    def test_exact_folder_name(self):
        """Each canonical folder name resolves to its DealStage."""
        for folder_name, expected_stage in FOLDER_TO_STAGE.items():
            assert resolve_stage(folder_name) == expected_stage

    def test_full_path_with_deal_name(self):
        """Folder path components are checked individually."""
        result = resolve_stage("Deals/1) Initial UW and Review/The Clubhouse")
        assert result == DealStage.INITIAL_REVIEW

    def test_dead_deals_folder(self):
        result = resolve_stage("Deals/0) Dead Deals/Old Property")
        assert result == DealStage.DEAD

    def test_active_review_folder(self):
        result = resolve_stage("Deals/2) Active UW and Review/SomeDeal")
        assert result == DealStage.ACTIVE_REVIEW

    def test_under_contract_folder(self):
        result = resolve_stage("Deals/3) Deals Under Contract/Pending")
        assert result == DealStage.UNDER_CONTRACT

    def test_closed_deals_folder(self):
        result = resolve_stage("Deals/4) Closed Deals/AcquiredProp")
        assert result == DealStage.CLOSED

    def test_realized_deals_folder(self):
        result = resolve_stage("Deals/5) Realized Deals/SoldProp")
        assert result == DealStage.REALIZED

    def test_no_match_returns_none(self):
        """Paths without a canonical folder return None."""
        assert resolve_stage("Deals/Other/SomeProp") is None
        assert resolve_stage("Random/Path") is None
        assert resolve_stage("") is None

    def test_case_insensitive(self):
        """Folder name matching is case-insensitive."""
        result = resolve_stage("Deals/0) dead deals/SomeProperty")
        assert result == DealStage.DEAD

    def test_deal_named_dead_no_false_positive(self):
        """A deal named 'Dead Creek Apartments' should NOT match dead stage.

        This was the key bug with the old substring matching — now we match
        on full path components, so deal names don't trigger false matches.
        """
        result = resolve_stage("Deals/2) Active UW and Review/Dead Creek Apartments")
        assert result == DealStage.ACTIVE_REVIEW

    def test_windows_backslash_paths(self):
        """Windows-style backslash paths are normalised."""
        result = resolve_stage("Deals\\1) Initial UW and Review\\The Clubhouse")
        assert result == DealStage.INITIAL_REVIEW

    def test_non_canonical_folders_return_none(self):
        """Folder names like 'Archive', 'Pipeline' are not canonical or aliased."""
        assert resolve_stage("Deals/Archive/OldDeal") is None
        assert resolve_stage("Deals/Pipeline/NewDeal") is None

    def test_alias_folders_resolve_via_alias(self):
        """Non-canonical folder names that match aliases still resolve."""
        assert resolve_stage("Deals/LOI/DealInLOI") == DealStage.ACTIVE_REVIEW
        assert resolve_stage("Deals/Due Diligence/DDDeal") == DealStage.UNDER_CONTRACT


class TestStageAliases:
    """Tests for STAGE_ALIASES and alias resolution in resolve_stage()."""

    def test_all_aliases_map_to_valid_stages(self):
        """Every alias value is a valid DealStage member."""
        for alias, stage in STAGE_ALIASES.items():
            assert isinstance(stage, DealStage), (
                f"Alias '{alias}' maps to non-DealStage: {stage}"
            )

    def test_all_stages_have_at_least_one_alias(self):
        """Every DealStage has at least one alias entry."""
        aliased_stages = set(STAGE_ALIASES.values())
        for stage in DealStage:
            assert stage in aliased_stages, f"DealStage.{stage.name} has no alias"

    def test_alias_keys_are_lowercase(self):
        """All alias keys should be lowercase for case-insensitive lookup."""
        for alias in STAGE_ALIASES:
            assert alias == alias.lower(), f"Alias key '{alias}' is not lowercase"

    def test_dead_aliases(self):
        """Dead stage aliases resolve correctly."""
        for alias in ["dead", "dead deal", "dead deals", "passed", "declined"]:
            result = resolve_stage(f"Deals/{alias}/SomeDeal")
            assert result == DealStage.DEAD, f"Alias '{alias}' did not resolve to DEAD"

    def test_initial_review_aliases(self):
        """Initial review aliases resolve correctly."""
        for alias in [
            "initial review",
            "initial uw",
            "initial underwriting",
            "new",
            "screening",
        ]:
            result = resolve_stage(f"Deals/{alias}/SomeDeal")
            assert result == DealStage.INITIAL_REVIEW, (
                f"Alias '{alias}' did not resolve to INITIAL_REVIEW"
            )

    def test_active_review_aliases(self):
        """Active review aliases resolve correctly."""
        for alias in [
            "active review",
            "active uw",
            "loi",
            "loi submitted",
            "best and final",
        ]:
            result = resolve_stage(f"Deals/{alias}/SomeDeal")
            assert result == DealStage.ACTIVE_REVIEW, (
                f"Alias '{alias}' did not resolve to ACTIVE_REVIEW"
            )

    def test_under_contract_aliases(self):
        """Under contract aliases resolve correctly."""
        for alias in ["under contract", "contracted", "psa", "due diligence"]:
            result = resolve_stage(f"Deals/{alias}/SomeDeal")
            assert result == DealStage.UNDER_CONTRACT, (
                f"Alias '{alias}' did not resolve to UNDER_CONTRACT"
            )

    def test_closed_aliases(self):
        """Closed stage aliases resolve correctly."""
        for alias in ["closed", "closed deal", "closed deals", "acquired"]:
            result = resolve_stage(f"Deals/{alias}/SomeDeal")
            assert result == DealStage.CLOSED, (
                f"Alias '{alias}' did not resolve to CLOSED"
            )

    def test_realized_aliases(self):
        """Realized stage aliases resolve correctly."""
        for alias in [
            "realized",
            "realized deal",
            "realized deals",
            "exited",
            "disposed",
        ]:
            result = resolve_stage(f"Deals/{alias}/SomeDeal")
            assert result == DealStage.REALIZED, (
                f"Alias '{alias}' did not resolve to REALIZED"
            )

    def test_alias_case_insensitive(self):
        """Alias matching is case-insensitive."""
        assert resolve_stage("Deals/LOI/SomeDeal") == DealStage.ACTIVE_REVIEW
        assert resolve_stage("Deals/Loi/SomeDeal") == DealStage.ACTIVE_REVIEW
        assert resolve_stage("Deals/PSA/SomeDeal") == DealStage.UNDER_CONTRACT
        assert resolve_stage("Deals/Dead Deal/SomeDeal") == DealStage.DEAD

    def test_canonical_folder_takes_priority_over_alias(self):
        """When a path has both a canonical folder and an alias, canonical wins."""
        # "dead" is an alias but "0) Dead Deals" is canonical — canonical should win
        result = resolve_stage("Deals/0) Dead Deals/dead/SubFolder")
        assert result == DealStage.DEAD

    def test_canonical_preferred_over_alias_different_stages(self):
        """Canonical folder match in pass 1 takes priority over alias in pass 2.

        The path contains canonical folder "2) Active UW and Review" and also
        a component "closed" which is an alias for CLOSED. The canonical match
        should take precedence.
        """
        result = resolve_stage("Deals/2) Active UW and Review/closed deal notes")
        assert result == DealStage.ACTIVE_REVIEW

    def test_alias_no_false_positive_on_deal_names(self):
        """A deal named 'LOI' inside a canonical folder should not override the folder."""
        result = resolve_stage("Deals/4) Closed Deals/LOI Phase 2")
        assert result == DealStage.CLOSED


class TestStageFolderMapConsistency:
    """Verify the derived mappings are consistent with FOLDER_TO_STAGE."""

    def test_stage_folder_map_values(self):
        """STAGE_FOLDER_MAP has string values matching DealStage.value."""
        for folder_name, stage_str in STAGE_FOLDER_MAP.items():
            assert folder_name in FOLDER_TO_STAGE
            assert FOLDER_TO_STAGE[folder_name].value == stage_str

    def test_stage_to_folder_reverse(self):
        """STAGE_TO_FOLDER is the exact inverse of FOLDER_TO_STAGE."""
        for stage, folder in STAGE_TO_FOLDER.items():
            assert FOLDER_TO_STAGE[folder] == stage

    def test_all_deal_stages_covered(self):
        """Every DealStage member has a folder mapping."""
        mapped_stages = set(FOLDER_TO_STAGE.values())
        for stage in DealStage:
            assert stage in mapped_stages, (
                f"DealStage.{stage.name} has no folder mapping"
            )


# ── StageChangeLog model + audit tests ─────────────────────────────────────


@pytest.mark.asyncio
async def test_change_deal_stage_creates_log(db_session: AsyncSession, test_deal: Deal):
    """change_deal_stage() creates a StageChangeLog entry."""
    original_stage = test_deal.stage  # ACTIVE_REVIEW from fixture

    log = await change_deal_stage(
        db=db_session,
        deal=test_deal,
        new_stage=DealStage.UNDER_CONTRACT,
        source=StageChangeSource.USER_KANBAN,
        changed_by_user_id=1,
        reason="Dragged on Kanban board",
    )

    assert log.id is not None
    assert log.deal_id == test_deal.id
    assert log.old_stage == original_stage.value
    assert log.new_stage == DealStage.UNDER_CONTRACT.value
    assert log.source == StageChangeSource.USER_KANBAN
    assert log.changed_by_user_id == 1
    assert log.reason == "Dragged on Kanban board"
    assert log.created_at is not None


@pytest.mark.asyncio
async def test_change_deal_stage_updates_deal(
    db_session: AsyncSession, test_deal: Deal
):
    """change_deal_stage() sets deal.stage and deal.stage_updated_at."""
    assert test_deal.stage == DealStage.ACTIVE_REVIEW
    assert test_deal.stage_updated_at is None  # not set in fixture

    await change_deal_stage(
        db=db_session,
        deal=test_deal,
        new_stage=DealStage.CLOSED,
        source=StageChangeSource.SHAREPOINT_SYNC,
    )

    assert test_deal.stage == DealStage.CLOSED
    assert test_deal.stage_updated_at is not None


@pytest.mark.asyncio
async def test_change_deal_stage_sharepoint_source(
    db_session: AsyncSession, test_deal: Deal
):
    """StageChangeLog with SHAREPOINT_SYNC source."""
    log = await change_deal_stage(
        db=db_session,
        deal=test_deal,
        new_stage=DealStage.DEAD,
        source=StageChangeSource.SHAREPOINT_SYNC,
        reason="File moved to 0) Dead Deals folder",
    )
    assert log.source == StageChangeSource.SHAREPOINT_SYNC
    assert log.changed_by_user_id is None


@pytest.mark.asyncio
async def test_change_deal_stage_extraction_source(
    db_session: AsyncSession, test_deal: Deal
):
    """StageChangeLog with EXTRACTION_SYNC source."""
    log = await change_deal_stage(
        db=db_session,
        deal=test_deal,
        new_stage=DealStage.INITIAL_REVIEW,
        source=StageChangeSource.EXTRACTION_SYNC,
        reason="Stage inferred from extraction folder structure",
    )
    assert log.source == StageChangeSource.EXTRACTION_SYNC


@pytest.mark.asyncio
async def test_change_deal_stage_manual_override(
    db_session: AsyncSession, test_deal: Deal
):
    """StageChangeLog with MANUAL_OVERRIDE source."""
    log = await change_deal_stage(
        db=db_session,
        deal=test_deal,
        new_stage=DealStage.REALIZED,
        source=StageChangeSource.MANUAL_OVERRIDE,
        changed_by_user_id=42,
        reason="Admin correction",
    )
    assert log.source == StageChangeSource.MANUAL_OVERRIDE
    assert log.changed_by_user_id == 42


@pytest.mark.asyncio
async def test_multiple_stage_changes_create_history(
    db_session: AsyncSession, test_deal: Deal
):
    """Multiple stage changes create multiple log entries."""
    transitions = [
        (DealStage.UNDER_CONTRACT, StageChangeSource.USER_KANBAN),
        (DealStage.CLOSED, StageChangeSource.USER_KANBAN),
        (DealStage.REALIZED, StageChangeSource.MANUAL_OVERRIDE),
    ]

    for new_stage, source in transitions:
        await change_deal_stage(
            db=db_session,
            deal=test_deal,
            new_stage=new_stage,
            source=source,
        )

    await db_session.commit()

    result = await db_session.execute(
        select(StageChangeLog)
        .where(StageChangeLog.deal_id == test_deal.id)
        .order_by(StageChangeLog.created_at.asc())
    )
    logs = list(result.scalars().all())

    assert len(logs) == 3
    assert logs[0].new_stage == "under_contract"
    assert logs[1].old_stage == "under_contract"
    assert logs[1].new_stage == "closed"
    assert logs[2].old_stage == "closed"
    assert logs[2].new_stage == "realized"


@pytest.mark.asyncio
async def test_stage_updated_at_always_set(db_session: AsyncSession, test_deal: Deal):
    """stage_updated_at is set on every call to change_deal_stage."""
    assert test_deal.stage_updated_at is None

    await change_deal_stage(
        db=db_session,
        deal=test_deal,
        new_stage=DealStage.UNDER_CONTRACT,
        source=StageChangeSource.USER_KANBAN,
    )
    first_ts = test_deal.stage_updated_at
    assert first_ts is not None

    await change_deal_stage(
        db=db_session,
        deal=test_deal,
        new_stage=DealStage.CLOSED,
        source=StageChangeSource.USER_KANBAN,
    )
    second_ts = test_deal.stage_updated_at
    assert second_ts is not None
    assert second_ts >= first_ts


# ── API endpoint tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stage_history_endpoint(client, db_session, test_deal, auth_headers):
    """GET /api/v1/deals/{deal_id}/stage-history returns audit log."""
    # Create some stage changes
    await change_deal_stage(
        db=db_session,
        deal=test_deal,
        new_stage=DealStage.UNDER_CONTRACT,
        source=StageChangeSource.USER_KANBAN,
        changed_by_user_id=1,
    )
    await change_deal_stage(
        db=db_session,
        deal=test_deal,
        new_stage=DealStage.CLOSED,
        source=StageChangeSource.SHAREPOINT_SYNC,
        reason="File moved",
    )
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/deals/{test_deal.id}/stage-history",
        headers=auth_headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["deal_id"] == test_deal.id
    assert data["total"] == 2
    assert len(data["history"]) == 2
    # Most recent first
    assert data["history"][0]["new_stage"] == "closed"
    assert data["history"][1]["new_stage"] == "under_contract"


@pytest.mark.asyncio
async def test_stage_history_endpoint_empty(
    client, db_session, test_deal, auth_headers
):
    """Stage history returns empty list when no changes recorded."""
    resp = await client.get(
        f"/api/v1/deals/{test_deal.id}/stage-history",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["history"] == []


@pytest.mark.asyncio
async def test_stage_history_endpoint_404(client, auth_headers):
    """Stage history returns 404 for nonexistent deal."""
    resp = await client.get(
        "/api/v1/deals/99999/stage-history",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_stage_history_endpoint_no_auth(client, test_deal):
    """Stage history requires authentication."""
    resp = await client.get(
        f"/api/v1/deals/{test_deal.id}/stage-history",
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_kanban_stage_update_creates_audit_log(
    client, db_session, test_deal, admin_auth_headers
):
    """PATCH /{deal_id}/stage creates a StageChangeLog via Kanban flow."""
    resp = await client.patch(
        f"/api/v1/deals/{test_deal.id}/stage",
        json={"stage": "under_contract"},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 200

    # Verify audit log was created
    result = await db_session.execute(
        select(StageChangeLog).where(StageChangeLog.deal_id == test_deal.id)
    )
    logs = list(result.scalars().all())
    assert len(logs) == 1
    assert logs[0].old_stage == "active_review"
    assert logs[0].new_stage == "under_contract"
    assert logs[0].source == StageChangeSource.USER_KANBAN


@pytest.mark.asyncio
async def test_stage_history_response_fields(
    client, db_session, test_deal, auth_headers
):
    """Verify all expected fields are present in stage history response."""
    await change_deal_stage(
        db=db_session,
        deal=test_deal,
        new_stage=DealStage.DEAD,
        source=StageChangeSource.MANUAL_OVERRIDE,
        changed_by_user_id=1,
        reason="Deal fell through",
    )
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/deals/{test_deal.id}/stage-history",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    entry = resp.json()["history"][0]

    assert "id" in entry
    assert "deal_id" in entry
    assert "old_stage" in entry
    assert "new_stage" in entry
    assert "source" in entry
    assert "changed_by_user_id" in entry
    assert "reason" in entry
    assert "created_at" in entry
    assert entry["source"] == "manual_override"
    assert entry["reason"] == "Deal fell through"
