import logging
from src.config import GROQ_KEYS, OPENROUTER_API_KEY
from src.utils.key_rotator import KeyRotator
from src.utils.tag_cleaner import clean_tag

logger = logging.getLogger(__name__)
_groq_rotator = KeyRotator(GROQ_KEYS, "Groq")


async def suggest_tag(title: str, platform: str, existing_tags: list[str]) -> str:
    """Ask AI to suggest a hierarchical tag for the given content."""
    tags_hint = "\n".join(existing_tags[:50]) if existing_tags else "none yet"
    prompt = f"""You are a personal content organizer. Suggest ONE tag for this saved link.

Platform: {platform}
Title: {title}

Existing tags in the user's system (use these when relevant, or create a new one):
{tags_hint}

Rules:
- Use hierarchical format with / separator (e.g. dev/react, clothes/man/winter, productivity/tools)
- Pick the deepest relevant tag you can
- If it fits an existing tag or subtag, use it
- Only return the tag, nothing else. No explanation.

Tag:"""

    if _groq_rotator.has_keys():
        try:
            return await _groq_tag(prompt)
        except RuntimeError as e:
            logger.warning(f"Groq tagging exhausted: {e}")

    if OPENROUTER_API_KEY:
        try:
            return await _openrouter_tag(prompt)
        except RuntimeError as e:
            logger.warning(f"OpenRouter tagging failed: {e}")

    return "uncategorized"


async def retag_all(links: list[dict], existing_tags: list[str]) -> list[tuple[int, str]]:
    """Re-suggest tags for a list of links. Returns [(id, new_tag), ...]"""
    results = []
    for link in links:
        try:
            new_tag = await suggest_tag(
                link.get("title", ""),
                link.get("platform", "article"),
                existing_tags,
            )
            results.append((link["user_link_id"], new_tag))
        except Exception as e:
            logger.warning(f"retag failed for link {link['user_link_id']}: {e}")
    return results


async def _groq_tag(prompt: str) -> str:
    from groq import Groq, RateLimitError
    attempts = len(_groq_rotator.keys)
    for _ in range(attempts):
        try:
            client = Groq(api_key=_groq_rotator.current())
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=30,
                temperature=0.2,
            )
            tag = clean_tag(resp.choices[0].message.content)
            tag = tag.replace(" ", "_")
            return tag or "uncategorized"
        except RateLimitError:
            logger.warning("Groq tag key rate limited, rotating")
            try:
                _groq_rotator.rotate()
            except RuntimeError:
                break
        except Exception as e:
            raise RuntimeError(f"Groq tag error: {e}")
    raise RuntimeError("All Groq keys exhausted for tagging")


async def _openrouter_tag(prompt: str) -> str:
    import httpx
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
            json={"model": "mistralai/mistral-7b-instruct:free", "messages": [{"role": "user", "content": prompt}], "max_tokens": 30},
        )
    if resp.status_code != 200:
        raise RuntimeError(f"OpenRouter error: {resp.status_code}")
    tag = clean_tag(resp.json()["choices"][0]["message"]["content"])
    return tag.replace(" ", "_") or "uncategorized"
