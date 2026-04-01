import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.75


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    a, b = a.lower().strip(), b.lower().strip()
    return SequenceMatcher(None, a, b).ratio()


def find_smart_duplicates(new_title: str, new_desc: str, existing: list[dict]) -> list[dict]:
    """Return existing links that are likely the same content as the new one."""
    # Skip smart check entirely if new link has no title and no description
    if not new_title.strip() and not new_desc.strip():
        return []

    matches = []
    for link in existing:
        existing_title = link.get("title", "").strip()
        existing_desc = link.get("description", "").strip()

        # Skip comparison against links that also have no title/description
        if not existing_title and not existing_desc:
            continue

        title_score = _similarity(new_title, existing_title)
        desc_score = _similarity(new_desc, existing_desc)
        score = max(title_score, (title_score + desc_score) / 2)
        if score >= SIMILARITY_THRESHOLD:
            matches.append({**link, "_similarity": round(score, 2)})
    return sorted(matches, key=lambda x: x["_similarity"], reverse=True)[:3]


def group_all_duplicates(links: list[dict]) -> list[list[dict]]:
    """Scan all links and return groups of suspected duplicates."""
    used = set()
    groups = []

    for i, link in enumerate(links):
        if link["id"] in used:
            continue
        group = [link]
        for j, other in enumerate(links):
            if i == j or other["id"] in used:
                continue
            title_score = _similarity(link.get("title", ""), other.get("title", ""))
            desc_score = _similarity(link.get("description", ""), other.get("description", ""))
            score = max(title_score, (title_score + desc_score) / 2)
            if score >= SIMILARITY_THRESHOLD:
                group.append(other)

        if len(group) > 1:
            for item in group:
                used.add(item["id"])
            groups.append(group)

    return groups
