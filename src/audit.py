#!/usr/bin/env python3
"""
subscription-sanity: audit your RevenueCat config for common mistakes.
Usage: RC_API_KEY=sk_... python3 audit.py [--project-id proj...]
"""

import os, sys, json, argparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE = "https://api.revenuecat.com/v2"
PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"
WARN = "\033[33m⚠\033[0m"
INFO = "\033[34mℹ\033[0m"


def rc(path, key):
    req = Request(f"{BASE}{path}", headers={"Authorization": f"Bearer {key}"})
    try:
        with urlopen(req) as r:
            return json.loads(r.read())
    except HTTPError as e:
        return json.loads(e.read())


def check(condition, label, detail=""):
    status = PASS if condition else FAIL
    suffix = f"  ({detail})" if detail else ""
    print(f"  {status} {label}{suffix}")
    return condition


def warn(condition, label, detail=""):
    status = PASS if condition else WARN
    suffix = f"  ({detail})" if detail else ""
    print(f"  {status} {label}{suffix}")
    return condition


def audit_project(project_id, key):
    print(f"\n{'='*60}")
    print(f"Project: {project_id}")
    print(f"{'='*60}")
    issues = 0

    # Apps
    apps = rc(f"/projects/{project_id}/apps?limit=50", key).get("items", [])
    if not check(len(apps) > 0, "Has at least one app", f"{len(apps)} found"):
        issues += 1
        return issues
    print(f"  {INFO} Apps: {', '.join(a['name'] + ' (' + a['type'] + ')' for a in apps)}")

    # Products
    products = rc(f"/projects/{project_id}/products?limit=100", key).get("items", [])
    if not check(len(products) > 0, "Has products defined", f"{len(products)} found"):
        issues += 1

    # Entitlements
    entitlements = rc(f"/projects/{project_id}/entitlements?limit=100", key).get("items", [])
    if not check(len(entitlements) > 0, "Has entitlements defined", f"{len(entitlements)} found"):
        issues += 1
    else:
        for ent in entitlements:
            eid = ent["id"]
            ent_products = rc(f"/projects/{project_id}/entitlements/{eid}/products", key).get("items", [])
            if not check(len(ent_products) > 0,
                         f"Entitlement '{ent['lookup_key']}' has products attached",
                         f"{len(ent_products)} attached"):
                issues += 1

    # Offerings
    offerings = rc(f"/projects/{project_id}/offerings?limit=50", key).get("items", [])
    if not check(len(offerings) > 0, "Has offerings defined", f"{len(offerings)} found"):
        issues += 1
    else:
        current = [o for o in offerings if o.get("is_current")]
        if not check(len(current) > 0, "Has a current offering set"):
            issues += 1
        if not warn(len(current) < 2, "Only one offering is set as current",
                    f"{len(current)} current offerings — unexpected"):
            issues += 1

        for offering in offerings:
            oid = offering["id"]
            packages = rc(f"/projects/{project_id}/offerings/{oid}/packages?limit=50", key).get("items", [])
            label = f"Offering '{offering['lookup_key']}'"
            if not check(len(packages) > 0, f"{label} has packages", f"{len(packages)} found"):
                issues += 1
            else:
                for pkg in packages:
                    pid2 = pkg["id"]
                    pkg_products = rc(f"/projects/{project_id}/packages/{pid2}/products", key).get("items", [])
                    if not check(len(pkg_products) > 0,
                                 f"  Package '{pkg['lookup_key']}' has a product attached",
                                 f"{len(pkg_products)} attached"):
                        issues += 1

    return issues


def main():
    parser = argparse.ArgumentParser(description="Audit RevenueCat config for common mistakes")
    parser.add_argument("--project-id", help="Project ID (or set RC_PROJECT_ID env var)")
    args = parser.parse_args()

    key = os.environ.get("RC_API_KEY")
    if not key:
        print("Error: RC_API_KEY environment variable not set")
        sys.exit(1)

    project_id = args.project_id or os.environ.get("RC_PROJECT_ID")
    if not project_id:
        # Discover projects
        projects = rc("/projects", key).get("items", [])
        if not projects:
            print("No projects found for this API key")
            sys.exit(1)
        print(f"Found {len(projects)} project(s). Auditing all.")
        total_issues = sum(audit_project(p["id"], key) for p in projects)
    else:
        total_issues = audit_project(project_id, key)

    print(f"\n{'='*60}")
    if total_issues == 0:
        print(f"{PASS} All checks passed. Your RevenueCat config looks healthy.")
    else:
        print(f"{FAIL} {total_issues} issue(s) found. Fix them before going live.")
    print()


if __name__ == "__main__":
    main()
