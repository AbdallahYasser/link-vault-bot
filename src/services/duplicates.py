def group_similar_tags(tags: list[str]) -> list[list[str]]:
    """Group tags that normalize to the same string (spaces ↔ underscores, case-insensitive)."""
    def _normalize(t: str) -> str:
        return t.lower().replace(" ", "_").replace("-", "_")

    buckets: dict[str, list[str]] = {}
    for tag in tags:
        buckets.setdefault(_normalize(tag), []).append(tag)

    return [group for group in buckets.values() if len(group) > 1]
