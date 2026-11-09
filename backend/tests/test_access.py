import pytest

from app.services.access import can_access_institution


@pytest.mark.parametrize(
    "who,inst,expected",
    [
        ("admin", "kaveri", True),
        ("admin", "northfield", True),
        ("officer_south", "kaveri", True),
        ("officer_south", "malabar", True),
        ("officer_south", "northfield", False),  # other region
        ("inst_admin", "kaveri", True),
        ("inst_admin", "malabar", False),  # other institution, same region
        ("inst_staff", "kaveri", True),
        ("inst_staff", "northfield", False),
        ("verifier", "kaveri", False),  # verifiers never read institutions
    ],
)
def test_institution_scope(db, world, who, inst, expected):
    assert can_access_institution(db, world["users"][who], world[inst]) is expected
