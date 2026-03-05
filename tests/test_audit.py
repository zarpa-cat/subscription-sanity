"""Tests for subscription-sanity audit logic."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from audit import audit_project


# --- Fixtures ---


def _make_app(name: str = "TestApp", app_type: str = "app_store") -> dict:
    return {"id": "app1", "name": name, "type": app_type}


def _make_product(pid: str = "prod1", name: str = "Monthly") -> dict:
    return {"id": pid, "display_name": name, "type": "subscription", "state": "active"}


def _make_entitlement(eid: str = "entl1", key: str = "premium") -> dict:
    return {"id": eid, "lookup_key": key, "state": "active"}


def _make_offering(
    oid: str = "ofrng1", key: str = "default", is_current: bool = True
) -> dict:
    return {"id": oid, "lookup_key": key, "is_current": is_current}


def _make_package(pkgid: str = "pkge1", key: str = "$rc_monthly") -> dict:
    return {"id": pkgid, "lookup_key": key}


def _make_list(*items: dict) -> dict:
    return {"items": list(items)}


def _make_empty() -> dict:
    return {"items": []}


# --- Tests ---


def _mock_rc(responses: dict):
    """Return a mock rc_get that dispatches by path substring, longest match wins."""

    def _get(path: str, key: str) -> dict:
        # Sort by pattern length descending so more specific patterns win
        for pattern in sorted(responses.keys(), key=len, reverse=True):
            if pattern in path:
                return responses[pattern]
        return {"items": []}

    return _get


class TestHealthyConfig:
    def test_all_checks_pass(self):
        responses = {
            "/apps": _make_list(_make_app()),
            "/products": _make_list(_make_product()),
            "/entitlements/entl1/products": _make_list(_make_product()),
            "/entitlements": _make_list(_make_entitlement()),
            "/offerings": _make_list(_make_offering()),
            "/offerings/ofrng1/packages": _make_list(_make_package()),
            "/packages/pkge1/products": _make_list(_make_product()),
        }
        with patch("audit.rc_get", side_effect=_mock_rc(responses)):
            result = audit_project("projtest", "sk_test")
        assert result.issues == 0
        assert result.warnings == 0


class TestNoApps:
    def test_no_apps_returns_early(self):
        responses = {"/apps": _make_empty()}
        with patch("audit.rc_get", side_effect=_mock_rc(responses)):
            result = audit_project("projtest", "sk_test")
        assert result.issues == 1


class TestEntitlementWithNoProducts:
    def test_ungated_entitlement_is_issue(self):
        responses = {
            "/apps": _make_list(_make_app()),
            "/products": _make_list(_make_product()),
            "/entitlements": _make_list(_make_entitlement()),
            "/entitlements/entl1/products": _make_empty(),  # no products attached
            "/offerings": _make_list(_make_offering()),
            "/offerings/ofrng1/packages": _make_list(_make_package()),
            "/packages/pkge1/products": _make_list(_make_product()),
        }
        with patch("audit.rc_get", side_effect=_mock_rc(responses)):
            result = audit_project("projtest", "sk_test")
        assert result.issues >= 1


class TestNoCurrentOffering:
    def test_missing_current_offering_is_issue(self):
        responses = {
            "/apps": _make_list(_make_app()),
            "/products": _make_list(_make_product()),
            "/entitlements": _make_list(_make_entitlement()),
            "/entitlements/entl1/products": _make_list(_make_product()),
            "/offerings": _make_list(_make_offering(is_current=False)),  # not current
            "/offerings/ofrng1/packages": _make_list(_make_package()),
            "/packages/pkge1/products": _make_list(_make_product()),
        }
        with patch("audit.rc_get", side_effect=_mock_rc(responses)):
            result = audit_project("projtest", "sk_test")
        assert result.issues >= 1


class TestEmptyPackage:
    def test_package_with_no_product_is_issue(self):
        responses = {
            "/apps": _make_list(_make_app()),
            "/products": _make_list(_make_product()),
            "/entitlements": _make_list(_make_entitlement()),
            "/entitlements/entl1/products": _make_list(_make_product()),
            "/offerings": _make_list(_make_offering()),
            "/offerings/ofrng1/packages": _make_list(_make_package()),
            "/packages/pkge1/products": _make_empty(),  # empty package
        }
        with patch("audit.rc_get", side_effect=_mock_rc(responses)):
            result = audit_project("projtest", "sk_test")
        assert result.issues >= 1


class TestOfferingWithNoPackages:
    def test_empty_offering_is_issue(self):
        responses = {
            "/apps": _make_list(_make_app()),
            "/products": _make_list(_make_product()),
            "/entitlements": _make_list(_make_entitlement()),
            "/entitlements/entl1/products": _make_list(_make_product()),
            "/offerings": _make_list(_make_offering()),
            "/offerings/ofrng1/packages": _make_empty(),  # no packages
        }
        with patch("audit.rc_get", side_effect=_mock_rc(responses)):
            result = audit_project("projtest", "sk_test")
        assert result.issues >= 1
