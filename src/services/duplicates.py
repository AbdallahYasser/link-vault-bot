from src.utils.tag_cleaner import clean_tag


def group_similar_tags(tags: list[str]) -> list[list[str]]:
    """Group tags that normalize to the same string (spaces ↔ underscores, case-insensitive, invisible chars stripped)."""
    def _normalize(t: str) -> str:
        return clean_tag(t).replace(" ", "_").replace("-", "_")

    buckets: dict[str, list[str]] = {}
    for tag in tags:
        buckets.setdefault(_normalize(tag), []).append(tag)

    return [group for group in buckets.values() if len(group) > 1]
