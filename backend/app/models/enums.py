from enum import Enum


class Role(str, Enum):
    AICTE_ADMIN = "AICTE_ADMIN"
    AICTE_OFFICER = "AICTE_OFFICER"
    INSTITUTION_ADMIN = "INSTITUTION_ADMIN"
    INSTITUTION_STAFF = "INSTITUTION_STAFF"
    VERIFIER = "VERIFIER"


AICTE_ROLES = (Role.AICTE_ADMIN, Role.AICTE_OFFICER)
INSTITUTION_ROLES = (Role.INSTITUTION_ADMIN, Role.INSTITUTION_STAFF)


def check_in(column: str, values) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"
