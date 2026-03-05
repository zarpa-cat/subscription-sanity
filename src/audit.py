#!/usr/bin/env python3
"""
subscription-sanity: audit your RevenueCat config for common setup mistakes.

Usage:
    RC_API_KEY=sk_... uv run python src/audit.py
    RC_API_KEY=sk_... uv run python src/audit.py --project-id projXXX
"""

from __future__ import annotations

import json
import os
import sys
import argparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from dataclasses import dataclass

BASE_URL = "https://api.revenuecat.com/v2"

# ANSI colour codes
PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"
WARN = "\033[33m⚠\033[0m"
INFO = "\033[34mℹ\033[0m"


@dataclass
class AuditResult:
    issues: int = 0
    warnings: int = 0


def rc_get(path: str, key: str) -> dict:
    """Make a GET request to the RevenueCat v2 API."""
    req = Request(f"{BASE_URL}{path}", headers={"Authorization": f"Bearer {key}"})
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read())  # type: ignore[no-any-return]
    except HTTPError as e:
        return json.loads(e.read())  # type: ignore[no-any-return]


def check(condition: bool, label: str, detail: str = "") -> bool:
    status = PASS if condition else FAIL
    suffix = f"  ({detail})" if detail else ""
    print(f"  {status} {label}{suffix}")
    return condition


def warn(condition: bool, label: str, detail: str = "") -> bool:
    status = PASS if condition else WARN
    suffix = f"  ({detail})" if detail else ""
    print(f"  {status} {label}{suffix}")
    return condition


def audit_project(project_id: str, key: str) -> AuditResult:
    result = AuditResult()
    print(f"\n{'=' * 60}")
    print(f"Project: {project_id}")
    print(f"{'=' * 60}")

    # --- Apps ---
    apps_resp = rc_get(f"/projects/{project_id}/apps?limit=50", key)
    apps: list[dict] = apps_resp.get("items", [])
    if not check(len(apps) > 0, "Has at least one app", f"{len(apps)} found"):
        result.issues += 1
        return result  # nothing else to check without apps

    app_names = ", ".join(f"{a['name']} ({a['type']})" for a in apps)
    print(f"  {INFO} Apps: {app_names}")

    # --- Products ---
    products_resp = rc_get(f"/projects/{project_id}/products?limit=100", key)
    products: list[dict] = products_resp.get("items", [])
    if not check(len(products) > 0, "Has products defined", f"{len(products)} found"):
        result.issues += 1

    # --- Entitlements ---
    ents_resp = rc_get(f"/projects/{project_id}/entitlements?limit=100", key)
    entitlements: list[dict] = ents_resp.get("items", [])
    if not check(
        len(entitlements) > 0, "Has entitlements defined", f"{len(entitlements)} found"
    ):
        result.issues += 1
    else:
        for ent in entitlements:
            eid = ent["id"]
            ent_products_resp = rc_get(
                f"/projects/{project_id}/entitlements/{eid}/products", key
            )
            ent_products: list[dict] = ent_products_resp.get("items", [])
            if not check(
                len(ent_products) > 0,
                f"Entitlement '{ent['lookup_key']}' has products attached",
                f"{len(ent_products)} attached",
            ):
                result.issues += 1

    # --- Offerings ---
    offerings_resp = rc_get(f"/projects/{project_id}/offerings?limit=50", key)
    offerings: list[dict] = offerings_resp.get("items", [])
    if not check(
        len(offerings) > 0, "Has offerings defined", f"{len(offerings)} found"
    ):
        result.issues += 1
        return result

    current_offerings = [o for o in offerings if o.get("is_current")]
    if not check(len(current_offerings) > 0, "Has a current offering set"):
        result.issues += 1
    if not warn(
        len(current_offerings) <= 1,
        "Only one offering marked as current",
        f"{len(current_offerings)} found",
    ):
        result.warnings += 1

    for offering in offerings:
        oid = offering["id"]
        pkgs_resp = rc_get(
            f"/projects/{project_id}/offerings/{oid}/packages?limit=50", key
        )
        packages: list[dict] = pkgs_resp.get("items", [])
        label = f"Offering '{offering['lookup_key']}'"

        if not check(
            len(packages) > 0, f"{label} has packages", f"{len(packages)} found"
        ):
            result.issues += 1
            continue

        for pkg in packages:
            pkg_id = pkg["id"]
            pkg_prods_resp = rc_get(
                f"/projects/{project_id}/packages/{pkg_id}/products", key
            )
            pkg_products: list[dict] = pkg_prods_resp.get("items", [])
            if not check(
                len(pkg_products) > 0,
                f"  Package '{pkg['lookup_key']}' has a product attached",
                f"{len(pkg_products)} attached",
            ):
                result.issues += 1

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit RevenueCat config for common setup mistakes"
    )
    parser.add_argument(
        "--project-id", help="Project ID (or set RC_PROJECT_ID env var)"
    )
    args = parser.parse_args()

    key = os.environ.get("RC_API_KEY", "")
    if not key:
        print("Error: RC_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    project_id = args.project_id or os.environ.get("RC_PROJECT_ID", "")

    if project_id:
        results = [audit_project(project_id, key)]
    else:
        projects_resp = rc_get("/projects", key)
        projects: list[dict] = projects_resp.get("items", [])
        if not projects:
            print("No projects found for this API key", file=sys.stderr)
            sys.exit(1)
        print(f"Found {len(projects)} project(s). Auditing all.")
        results = [audit_project(p["id"], key) for p in projects]

    total_issues = sum(r.issues for r in results)
    total_warnings = sum(r.warnings for r in results)

    print(f"\n{'=' * 60}")
    if total_issues == 0:
        print(f"{PASS} All checks passed.", end="")
        if total_warnings:
            print(f" {total_warnings} warning(s) to review.")
        else:
            print(" Your RevenueCat config looks healthy.")
    else:
        print(f"{FAIL} {total_issues} issue(s) found. Fix before going live.")
    print()


if __name__ == "__main__":
    main()
