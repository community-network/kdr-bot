import asyncpg
from sqlalchemy.exc import IntegrityError


def is_unique_violation(ex: IntegrityError):
    if ex.orig is None or ex.orig.__cause__.__class__ != asyncpg.UniqueViolationError:
        return False

    return True
