"""R1 on a plan: the prior_art section names each thing the plan adds."""

from druks_house_rules import plans

PLAN = """# Add notes

Add a class `Note` in models.py and a new setting `notes_limit`.

## prior_art

- `Note`: no existing model holds a note; `Artifact` holds files, not text.
- `notes_limit`: no setting caps a list today.
"""


def test_plan_with_prior_art_passes():
    assert plans.check(PLAN) == []


def test_plan_without_prior_art_is_denied():
    plan = PLAN.split("## prior_art")[0]
    assert [finding.rule for finding in plans.check(plan)] == ["R1"]
    assert "no prior_art section" in plans.check(plan)[0].message


def test_prior_art_must_name_each_addition():
    plan = PLAN.replace("- `notes_limit`: no setting caps a list today.\n", "")
    assert [finding.message for finding in plans.check(plan)] == [
        "prior_art does not name setting notes_limit; name the existing primitive and the "
        "verified gap, or drop it"
    ]


def test_bold_heading_and_name_first_order():
    plan = "Adds a `redis` dependency.\n\n**Prior art**: `redis` is the one client; none today.\n"
    assert plans.check(plan) == []
