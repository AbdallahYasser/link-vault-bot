import re

# Unicode invisible/directional format characters that Arabic keyboards inject
_INVISIBLE = re.compile(r'[\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]')


def clean_tag(tag: str) -> str:
    """Strip invisible Unicode chars, lowercase, strip leading/trailing slashes."""
    return _INVISIBLE.sub('', tag).strip().lower().strip("/")
