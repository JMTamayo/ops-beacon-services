from sqlalchemy.exc import IntegrityError


def integrity_error_detail(exc: IntegrityError) -> str:
    """Map common PostgreSQL integrity failures to a short API message."""
    orig = exc.orig
    code = getattr(orig, "pgcode", None)
    if code == "23P01":
        return (
            "Assignment time range overlaps another assignment for the same device "
            "(exclusion constraint)."
        )
    if code == "23514":
        return "Check constraint failed (e.g. ended_at must be after started_at)."
    if code == "23503":
        return (
            "Foreign key violation: referenced row missing, or delete blocked by dependent rows."
        )
    if code == "23505":
        return "Unique constraint violated (e.g. entity name already exists)."
    text = str(orig or exc).lower()
    if "excl" in text and "overlap" in text:
        return (
            "Assignment time range overlaps another assignment for the same device "
            "(exclusion constraint)."
        )
    return "Database constraint violation."
