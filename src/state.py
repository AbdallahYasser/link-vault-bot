# Module-level shared state — simple dicts, no external dependencies
pending_tags: dict[int, int] = {}       # user_id -> link_id awaiting tag edit
pending_titles: dict[int, int] = {}     # user_id -> link_id awaiting title edit (existing links)
pending_new_links: dict[int, dict] = {} # user_id -> {url, original_url, platform} awaiting title for new link
reminders: dict[tuple, object] = {}     # (user_id, user_link_id) -> asyncio.Task
tag_merge_groups: dict[int, tuple] = {}  # group_id -> (user_id, [tag1, tag2, ...])
