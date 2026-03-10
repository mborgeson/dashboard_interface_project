"""Tests for RBAC permissions module.

Covers:
- Role enum and hierarchy
- CurrentUser permission checks
- Resource ownership checks
"""

import pytest
from fastapi import HTTPException

from app.core.permissions import (
    CurrentUser,
    Role,
    ROLE_HIERARCHY,
    check_resource_ownership,
)


# =============================================================================
# Role Enum Tests
# =============================================================================


class TestRoleEnum:
    """Tests for the Role StrEnum."""

    def test_role_values(self):
        assert Role.ADMIN == "admin"
        assert Role.MANAGER == "manager"
        assert Role.ANALYST == "analyst"
        assert Role.VIEWER == "viewer"

    def test_role_hierarchy_ordering(self):
        assert ROLE_HIERARCHY[Role.VIEWER] < ROLE_HIERARCHY[Role.ANALYST]
        assert ROLE_HIERARCHY[Role.ANALYST] < ROLE_HIERARCHY[Role.MANAGER]
        assert ROLE_HIERARCHY[Role.MANAGER] < ROLE_HIERARCHY[Role.ADMIN]

    def test_role_from_string(self):
        assert Role("admin") == Role.ADMIN
        assert Role("viewer") == Role.VIEWER

    def test_role_invalid_string_raises(self):
        with pytest.raises(ValueError):
            Role("superadmin")


# =============================================================================
# CurrentUser Tests
# =============================================================================


class TestCurrentUser:
    """Tests for CurrentUser permission methods."""

    @pytest.fixture
    def admin(self):
        return CurrentUser(id=1, email="admin@test.com", role=Role.ADMIN)

    @pytest.fixture
    def manager(self):
        return CurrentUser(id=2, email="mgr@test.com", role=Role.MANAGER)

    @pytest.fixture
    def analyst(self):
        return CurrentUser(id=3, email="analyst@test.com", role=Role.ANALYST)

    @pytest.fixture
    def viewer(self):
        return CurrentUser(id=4, email="viewer@test.com", role=Role.VIEWER)

    # --- has_role (hierarchical check) ---

    def test_admin_has_all_roles(self, admin):
        assert admin.has_role(Role.ADMIN) is True
        assert admin.has_role(Role.MANAGER) is True
        assert admin.has_role(Role.ANALYST) is True
        assert admin.has_role(Role.VIEWER) is True

    def test_viewer_only_has_viewer_role(self, viewer):
        assert viewer.has_role(Role.VIEWER) is True
        assert viewer.has_role(Role.ANALYST) is False
        assert viewer.has_role(Role.MANAGER) is False
        assert viewer.has_role(Role.ADMIN) is False

    def test_manager_has_manager_and_below(self, manager):
        assert manager.has_role(Role.MANAGER) is True
        assert manager.has_role(Role.ANALYST) is True
        assert manager.has_role(Role.VIEWER) is True
        assert manager.has_role(Role.ADMIN) is False

    # --- has_exact_role ---

    def test_has_exact_role(self, analyst):
        assert analyst.has_exact_role(Role.ANALYST) is True
        assert analyst.has_exact_role(Role.VIEWER) is False

    # --- Convenience permission methods ---

    def test_is_admin(self, admin, manager):
        assert admin.is_admin() is True
        assert manager.is_admin() is False

    def test_can_manage_users(self, admin, manager):
        assert admin.can_manage_users() is True
        assert manager.can_manage_users() is False

    def test_can_approve_deals(self, admin, manager, analyst):
        assert admin.can_approve_deals() is True
        assert manager.can_approve_deals() is True
        assert analyst.can_approve_deals() is False

    def test_can_modify_data(self, admin, manager, analyst, viewer):
        assert admin.can_modify_data() is True
        assert manager.can_modify_data() is True
        assert analyst.can_modify_data() is True
        assert viewer.can_modify_data() is False

    # --- Edge cases ---

    def test_inactive_user_attributes(self):
        user = CurrentUser(
            id=10, email="disabled@test.com", role=Role.ANALYST, is_active=False
        )
        assert user.is_active is False
        # Permission checks still work (enforcement is at dependency level)
        assert user.can_modify_data() is True


# =============================================================================
# Resource Ownership Tests
# =============================================================================


class TestCheckResourceOwnership:
    def test_owner_can_access(self):
        user = CurrentUser(id=5, email="user@test.com", role=Role.ANALYST)
        assert check_resource_ownership(user, resource_owner_id=5) is True

    def test_non_owner_cannot_access(self):
        user = CurrentUser(id=5, email="user@test.com", role=Role.ANALYST)
        assert check_resource_ownership(user, resource_owner_id=99) is False

    def test_admin_override_allows_access(self):
        admin = CurrentUser(id=1, email="admin@test.com", role=Role.ADMIN)
        assert check_resource_ownership(admin, resource_owner_id=99) is True

    def test_admin_override_disabled(self):
        admin = CurrentUser(id=1, email="admin@test.com", role=Role.ADMIN)
        result = check_resource_ownership(
            admin, resource_owner_id=99, allow_admin_override=False
        )
        assert result is False

    def test_non_admin_no_override(self):
        manager = CurrentUser(id=2, email="mgr@test.com", role=Role.MANAGER)
        assert check_resource_ownership(manager, resource_owner_id=99) is False
