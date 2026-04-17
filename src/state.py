# Module-level shared state — simple dicts, no external dependencies
pending_tags: dict[int, int] = {}       # user_id -> link_id awaiting tag edit
pending_titles: dict[int, int] = {}     # user_id -> link_id awaiting title edit (existing links)
pending_new_links: dict[int, dict] = {} # user_id -> {url, original_url, platform} awaiting title for new link
reminders: dict[tuple, object] = {}     # (user_id, user_link_id) -> asyncio.Task
tag_merge_groups: dict[int, tuple] = {}  # group_id -> (user_id, [tag1, tag2, ...])
pending_imports: dict[int, list] = {}    # user_id -> link dicts awaiting import decision
pending_import_tag: set = set()          # user_ids waiting to type a custom tag for import
