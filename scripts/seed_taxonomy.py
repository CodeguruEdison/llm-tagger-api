"""
Seed script — creates full taxonomy from requirements document.

Creates:
  - 8 categories
  - 25+ tags
  - 5 rules with conditions

Usage:
    uv run python scripts/seed_taxonomy.py
    uv run python scripts/seed_taxonomy.py --base-url http://localhost:8000
"""
import asyncio
import httpx
import argparse

BASE_URL = "http://localhost:8000"


async def create_category(client: httpx.AsyncClient, data: dict) -> dict:
    response = await client.post("/taxonomy/categories", json=data)
    if response.status_code == 201:
        result = response.json()
        print(f"  ✓ Category: {data['name']} ({result['id']})")
        return result
    elif response.status_code == 409:
        print(f"  ⚠ Category already exists: {data['name']}")
        # fetch existing
        r = await client.get("/taxonomy/categories")
        categories = r.json()
        return next((c for c in categories if c["slug"] == data["slug"]), {})
    else:
        print(f"  ✗ Failed to create category {data['name']}: {response.text}")
        return {}


async def create_tag(client: httpx.AsyncClient, data: dict) -> dict:
    response = await client.post("/taxonomy/tags", json=data)
    if response.status_code == 201:
        result = response.json()
        print(f"    ✓ Tag: {data['name']} ({result['id']})")
        return result
    elif response.status_code == 409:
        print(f"    ⚠ Tag already exists: {data['name']}")
        r = await client.get("/taxonomy/tags")
        tags = r.json()
        return next((t for t in tags if t["slug"] == data["slug"]), {})
    else:
        print(f"    ✗ Failed to create tag {data['name']}: {response.text}")
        return {}


async def create_rule(client: httpx.AsyncClient, data: dict) -> dict:
    response = await client.post("/rules", json=data)
    if response.status_code == 201:
        result = response.json()
        print(f"  ✓ Rule: {data['name']} ({result['id']})")
        return result
    else:
        print(f"  ✗ Failed to create rule {data['name']}: {response.text}")
        return {}


async def seed(base_url: str):
    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:

        # ── Check API is alive ─────────────────────────────
        try:
            r = await client.get("/health")
            print(f"✓ API is alive at {base_url}\n")
        except Exception:
            print(f"✗ Cannot reach API at {base_url}")
            return

        # ── Categories ────────────────────────────────────
        print("Creating categories...")

        categories_data = [
            {
                "name": "Parts",
                "slug": "parts",
                "description": "Issues related to parts procurement and availability",
                "is_active": True,
                "sort_order": 1,
            },
            {
                "name": "Customer",
                "slug": "customer",
                "description": "Customer-related interactions and issues",
                "is_active": True,
                "sort_order": 2,
            },
            {
                "name": "Insurance",
                "slug": "insurance",
                "description": "Insurance and claims-related items",
                "is_active": True,
                "sort_order": 3,
            },
            {
                "name": "Production",
                "slug": "production",
                "description": "Production status and concerns",
                "is_active": True,
                "sort_order": 4,
            },
            {
                "name": "Sublet",
                "slug": "sublet",
                "description": "Sublet-related activities",
                "is_active": True,
                "sort_order": 5,
            },
            {
                "name": "Rental",
                "slug": "rental",
                "description": "Rental car-related items",
                "is_active": True,
                "sort_order": 6,
            },
            {
                "name": "Communication",
                "slug": "communication",
                "description": "Communication tracking",
                "is_active": True,
                "sort_order": 7,
            },
            {
                "name": "Financial",
                "slug": "financial",
                "description": "Financial concerns",
                "is_active": True,
                "sort_order": 8,
            },
        ]

        categories = {}
        for cat_data in categories_data:
            cat = await create_category(client, cat_data)
            if cat:
                categories[cat_data["slug"]] = cat["id"]

        print()

        # ── Tags ──────────────────────────────────────────
        print("Creating tags...")

        tags_data = [
            # Parts
            {"category_slug": "parts", "name": "Parts Delay", "slug": "parts-delay",
             "description": "RO is waiting on parts from supplier, backordered, or ETA unknown",
             "color": "#FF6B6B", "icon": "clock", "priority": 1},
            {"category_slug": "parts", "name": "Parts Ordered", "slug": "parts-ordered",
             "description": "Parts have been ordered and are in transit",
             "color": "#FB923C", "icon": "package", "priority": 2},
            {"category_slug": "parts", "name": "Parts Received", "slug": "parts-received",
             "description": "Parts have arrived at the shop and are ready for installation",
             "color": "#22C55E", "icon": "package-check", "priority": 3},
            {"category_slug": "parts", "name": "Wrong Parts", "slug": "wrong-parts",
             "description": "Incorrect parts were delivered, need to return and reorder",
             "color": "#EF4444", "icon": "x-circle", "priority": 4},
            {"category_slug": "parts", "name": "Parts Return", "slug": "parts-return",
             "description": "Parts are being returned to supplier",
             "color": "#F97316", "icon": "package-x", "priority": 5},

            # Customer
            {"category_slug": "customer", "name": "Customer Concern", "slug": "customer-concern",
             "description": "Customer expressed dissatisfaction, filed complaint, or is unhappy with service or timeline",
             "color": "#EF4444", "icon": "alert-circle", "priority": 1},
            {"category_slug": "customer", "name": "Customer Contacted", "slug": "customer-contacted",
             "description": "Shop successfully reached customer with an update",
             "color": "#3B82F6", "icon": "phone", "priority": 2},
            {"category_slug": "customer", "name": "Customer No-Show", "slug": "customer-no-show",
             "description": "Customer did not show up for scheduled appointment or pickup",
             "color": "#F59E0B", "icon": "user-x", "priority": 3},
            {"category_slug": "customer", "name": "Customer Approval Needed", "slug": "customer-approval-needed",
             "description": "Waiting for customer to approve additional repairs or costs before proceeding",
             "color": "#8B5CF6", "icon": "user-check", "priority": 4},

            # Insurance
            {"category_slug": "insurance", "name": "Insurance Issue", "slug": "insurance-issue",
             "description": "General insurance-related problem including coverage disputes or claim issues",
             "color": "#6366F1", "icon": "shield", "priority": 1},
            {"category_slug": "insurance", "name": "Adjuster Needed", "slug": "adjuster-needed",
             "description": "Insurance adjuster needs to inspect vehicle or approve additional work",
             "color": "#8B5CF6", "icon": "user-search", "priority": 2},
            {"category_slug": "insurance", "name": "Supplement", "slug": "supplement",
             "description": "Additional damage found requiring insurance supplement approval before repairs can continue",
             "color": "#A855F7", "icon": "file-plus", "priority": 3},
            {"category_slug": "insurance", "name": "Total Loss", "slug": "total-loss",
             "description": "Vehicle may be declared a total loss by insurance company",
             "color": "#DC2626", "icon": "alert-triangle", "priority": 4},
            {"category_slug": "insurance", "name": "Coverage Issue", "slug": "coverage-issue",
             "description": "Insurance coverage dispute, denial, or unclear coverage for specific repairs",
             "color": "#EF4444", "icon": "shield-x", "priority": 5},

            # Production
            {"category_slug": "production", "name": "Priority", "slug": "priority",
             "description": "RO has been flagged as high priority requiring immediate attention",
             "color": "#EF4444", "icon": "zap", "priority": 1},
            {"category_slug": "production", "name": "Rush", "slug": "rush",
             "description": "Customer or management requested expedited repair completion",
             "color": "#F97316", "icon": "trending-up", "priority": 2},
            {"category_slug": "production", "name": "Hold", "slug": "hold",
             "description": "RO is on hold pending parts, approval, or customer decision",
             "color": "#6B7280", "icon": "pause-circle", "priority": 3},
            {"category_slug": "production", "name": "Quality Issue", "slug": "quality-issue",
             "description": "Repair quality concern identified during inspection or by customer",
             "color": "#DC2626", "icon": "alert-octagon", "priority": 4},
            {"category_slug": "production", "name": "Rework", "slug": "rework",
             "description": "Repair needs to be redone due to quality issue or incorrect work",
             "color": "#B91C1C", "icon": "rotate-ccw", "priority": 5},
            {"category_slug": "production", "name": "Behind Schedule", "slug": "behind-schedule",
             "description": "RO is past promised completion date or falling behind production schedule",
             "color": "#F59E0B", "icon": "calendar-x", "priority": 6},

            # Sublet
            {"category_slug": "sublet", "name": "Sublet Out", "slug": "sublet-out",
             "description": "Vehicle or part of repair sent to outside vendor",
             "color": "#0EA5E9", "icon": "external-link", "priority": 1},
            {"category_slug": "sublet", "name": "Sublet Delay", "slug": "sublet-delay",
             "description": "Outside vendor has delayed return of vehicle or sublet work",
             "color": "#F59E0B", "icon": "clock", "priority": 2},
            {"category_slug": "sublet", "name": "Sublet Complete", "slug": "sublet-complete",
             "description": "Sublet work has been completed and vehicle returned",
             "color": "#22C55E", "icon": "check-circle", "priority": 3},

            # Rental
            {"category_slug": "rental", "name": "Rental", "slug": "rental",
             "description": "Customer has a rental car associated with this repair",
             "color": "#06B6D4", "icon": "car", "priority": 1},
            {"category_slug": "rental", "name": "Rental Extension", "slug": "rental-extension",
             "description": "Rental car period needs to be extended due to repair delay",
             "color": "#F59E0B", "icon": "calendar-plus", "priority": 2},
            {"category_slug": "rental", "name": "Rental Expired", "slug": "rental-expired",
             "description": "Insurance-approved rental days have been exhausted",
             "color": "#EF4444", "icon": "calendar-x", "priority": 3},
            {"category_slug": "rental", "name": "No Rental", "slug": "no-rental",
             "description": "Customer does not have rental coverage or declined rental car",
             "color": "#6B7280", "icon": "car-off", "priority": 4},

            # Communication
            {"category_slug": "communication", "name": "Follow-Up Needed", "slug": "follow-up-needed",
             "description": "Action required — someone needs to follow up with customer or vendor",
             "color": "#F59E0B", "icon": "bell", "priority": 1},
            {"category_slug": "communication", "name": "Callback Requested", "slug": "callback-requested",
             "description": "Customer requested a callback from the shop",
             "color": "#3B82F6", "icon": "phone-incoming", "priority": 2},
            {"category_slug": "communication", "name": "Message Left", "slug": "message-left",
             "description": "Voicemail or message left for customer, awaiting response",
             "color": "#6B7280", "icon": "voicemail", "priority": 3},

            # Financial
            {"category_slug": "financial", "name": "Payment Issue", "slug": "payment-issue",
             "description": "Problem with payment including declined cards, insufficient funds, or billing disputes",
             "color": "#EF4444", "icon": "credit-card", "priority": 1},
            {"category_slug": "financial", "name": "Deductible", "slug": "deductible",
             "description": "Customer deductible discussion, dispute, or payment pending",
             "color": "#F59E0B", "icon": "dollar-sign", "priority": 2},
            {"category_slug": "financial", "name": "Authorization", "slug": "authorization",
             "description": "Waiting for financial authorization from insurance or customer to proceed",
             "color": "#8B5CF6", "icon": "file-check", "priority": 3},
        ]

        tags = {}
        for tag_data in tags_data:
            cat_slug = tag_data.pop("category_slug")
            cat_id = categories.get(cat_slug)
            if not cat_id:
                print(f"    ✗ No category found for slug: {cat_slug}")
                continue
            tag_data["category_id"] = cat_id
            tag_data["is_active"] = True
            tag = await create_tag(client, tag_data)
            if tag:
                tags[tag_data["slug"]] = tag["id"]

        print()

        # ── Rules ─────────────────────────────────────────
        print("Creating rules...")

        rules_data = [
            {
                "tag_id": tags.get("parts-delay"),
                "name": "Parts Delay Detection",
                "priority": 100,
                "is_enabled": True,
                "conditions": [
                    {
                        "condition_type": "KEYWORD_ANY",
                        "operator": "AND",
                        "values": [
                            "parts delay", "waiting on parts", "backordered",
                            "back ordered", "parts on order", "eta on parts",
                            "waiting for parts", "part is delayed",
                        ],
                    },
                    {
                        "condition_type": "KEYWORD_NONE",
                        "operator": "AND",
                        "values": [
                            "parts arrived", "parts received",
                            "parts are in", "parts came in",
                        ],
                    },
                ],
            },
            {
                "tag_id": tags.get("parts-received"),
                "name": "Parts Received Detection",
                "priority": 95,
                "is_enabled": True,
                "conditions": [
                    {
                        "condition_type": "KEYWORD_ANY",
                        "operator": "AND",
                        "values": [
                            "parts arrived", "parts received",
                            "parts came in", "parts are in",
                            "parts delivered",
                        ],
                    },
                ],
            },
            {
                "tag_id": tags.get("customer-concern"),
                "name": "Customer Concern Detection",
                "priority": 90,
                "is_enabled": True,
                "conditions": [
                    {
                        "condition_type": "KEYWORD_ANY",
                        "operator": "AND",
                        "values": [
                            "customer upset", "customer complaint",
                            "customer angry", "customer frustrated",
                            "escalation", "unhappy", "very upset",
                            "threatening", "bad review", "bbb",
                            "better business bureau", "contact adjuster",
                        ],
                    },
                ],
            },
            {
                "tag_id": tags.get("supplement"),
                "name": "Supplement Required Detection",
                "priority": 95,
                "is_enabled": True,
                "conditions": [
                    {
                        "condition_type": "KEYWORD_ANY",
                        "operator": "AND",
                        "values": [
                            "supplement", "supp needed", "additional damage",
                            "hidden damage", "teardown found", "found more damage",
                            "additional damage found", "need to submit supplement",
                        ],
                    },
                ],
            },
            {
                "tag_id": tags.get("insurance-issue"),
                "name": "Insurance Issue Detection",
                "priority": 85,
                "is_enabled": True,
                "conditions": [
                    {
                        "condition_type": "KEYWORD_ANY",
                        "operator": "AND",
                        "values": [
                            "adjuster", "insurance denied", "coverage issue",
                            "total loss", "waiting on approval", "claim denied",
                            "insurance problem", "coverage dispute",
                        ],
                    },
                ],
            },
            {
                "tag_id": tags.get("rental-extension"),
                "name": "Rental Extension Detection",
                "priority": 80,
                "is_enabled": True,
                "conditions": [
                    {
                        "condition_type": "KEYWORD_ANY",
                        "operator": "AND",
                        "values": [
                            "rental extension", "rental expired",
                            "enterprise", "hertz", "no rental",
                            "rental concern", "rental days",
                            "extend rental", "rental running out",
                        ],
                    },
                ],
            },
            {
                "tag_id": tags.get("message-left"),
                "name": "Message Left Detection",
                "priority": 70,
                "is_enabled": True,
                "conditions": [
                    {
                        "condition_type": "KEYWORD_ANY",
                        "operator": "AND",
                        "values": [
                            "left voicemail", "left a message",
                            "no answer", "voicemail", "message left",
                            "tried to reach", "called no answer",
                        ],
                    },
                ],
            },
            {
                "tag_id": tags.get("total-loss"),
                "name": "Total Loss Detection",
                "priority": 95,
                "is_enabled": True,
                "conditions": [
                    {
                        "condition_type": "KEYWORD_ANY",
                        "operator": "AND",
                        "values": [
                            "total loss", "totaled", "declare total",
                            "total loss threshold", "tl vehicle",
                        ],
                    },
                ],
            },
        ]

        for rule_data in rules_data:
            if not rule_data.get("tag_id"):
                print(f"  ✗ Skipping rule — tag not found: {rule_data['name']}")
                continue
            await create_rule(client, rule_data)

        print("\n✓ Seed complete!")
        print(f"  Categories: {len(categories)}")
        print(f"  Tags: {len(tags)}")
        print(f"  Rules: {len(rules_data)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="API base URL",
    )
    args = parser.parse_args()
    asyncio.run(seed(args.base_url))