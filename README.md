# subscription-sanity

Audit your RevenueCat project config for common setup mistakes before they cost you.

```
$ RC_API_KEY=sk_... python3 src/audit.py

============================================================
Project: projaf07dfb5
============================================================
  ✓ Has at least one app  (2 found)
  ℹ Apps: Test Store (test_store), zarpa-ios (app_store)
  ✓ Has products defined  (2 found)
  ✓ Has entitlements defined  (1 found)
  ✓ Entitlement 'premium' has products attached  (2 attached)
  ✓ Has offerings defined  (1 found)
  ✓ Has a current offering set
  ✓ Offering 'default' has packages  (2 found)
  ✓   Package '$rc_monthly' has a product attached  (1 attached)
  ✓   Package '$rc_annual' has a product attached  (1 attached)

============================================================
✓ All checks passed. Your RevenueCat config looks healthy.
```

---

## What it checks

**Apps**
- [ ] Project has at least one app

**Products**
- [ ] At least one product is defined

**Entitlements**
- [ ] At least one entitlement exists
- [ ] Every entitlement has products attached (ungated entitlements are invisible to users)

**Offerings**
- [ ] At least one offering exists
- [ ] A current offering is set (if not, the SDK returns nothing)
- [ ] No more than one offering is marked as current
- [ ] Every offering has packages
- [ ] Every package has a product attached (empty packages show nothing)

These are the checks that would have caught the most common RevenueCat setup bugs I've seen and made myself. An offering with no packages, or a package with no product, is silent — the SDK just shows nothing and you wonder why your paywall is empty.

---

## Usage

```bash
# Audit all projects on the key
RC_API_KEY=sk_... python3 src/audit.py

# Audit a specific project
RC_API_KEY=sk_... python3 src/audit.py --project-id projXXXXXXXX

# Or set both as env vars
export RC_API_KEY=sk_...
export RC_PROJECT_ID=projXXXXXXXX
python3 src/audit.py
```

**Requirements:** Python 3.7+, no dependencies beyond stdlib.

---

## Why this exists

Built by [Zarpa](https://zarpa-cat.github.io) during a RevenueCat API deep-dive session.
The checks come from real friction: the RC API is clean, but the setup sequence has enough
steps that it's easy to wire things up almost-correctly and have a silent failure.

An offering that's current but has no packages returns fine from the API — zero errors,
zero indication anything is wrong. Your paywall just shows nothing. This tool catches that.

---

## Roadmap

- [ ] Check for products with null duration (subscription without a duration set)
- [ ] Check for orphaned products (not attached to any entitlement or package)
- [ ] JSON output mode (`--json`) for CI integration
- [ ] GitHub Action wrapper
- [ ] Check API key permissions (secret key required for most endpoints)

Contributions welcome. Or just open an issue with a check you wish existed.
