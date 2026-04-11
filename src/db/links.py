import aiosqlite
from datetime import datetime
from src.config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL DEFAULT 0,
                user_link_id INTEGER NOT NULL DEFAULT 0,
                url          TEXT NOT NULL,
                original_url TEXT NOT NULL,
                title        TEXT,
                description  TEXT,
                platform     TEXT DEFAULT 'article',
                tag          TEXT DEFAULT 'uncategorized',
                status       TEXT DEFAULT 'unread',
                saved_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                done_at      DATETIME,
                UNIQUE(url, user_id)
            )
        """)
        async with db.execute("PRAGMA table_info(links)") as cur:
            columns = {row[1] for row in await cur.fetchall()}

        # Migration: add user_id if missing (very old schema)
        if "user_id" not in columns:
            await db.execute("DROP TABLE IF EXISTS links_old")
            await db.execute("ALTER TABLE links RENAME TO links_old")
            await db.execute("""
                CREATE TABLE links (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id      INTEGER NOT NULL DEFAULT 0,
                    user_link_id INTEGER NOT NULL DEFAULT 0,
                    url          TEXT NOT NULL,
                    original_url TEXT NOT NULL,
                    title        TEXT,
                    description  TEXT,
                    platform     TEXT DEFAULT 'article',
                    tag          TEXT DEFAULT 'uncategorized',
                    status       TEXT DEFAULT 'unread',
                    saved_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                    done_at      DATETIME,
                    UNIQUE(url, user_id)
                )
            """)
            await db.execute("""
                INSERT INTO links (user_id, user_link_id, url, original_url, title, description, platform, tag, status, saved_at, updated_at, done_at)
                SELECT 0, 0, url, original_url, title, description, platform, tag, status, saved_at, updated_at, done_at FROM links_old
            """)
            await db.execute("DROP TABLE links_old")

        # Migration: add user_link_id if missing
        elif "user_link_id" not in columns:
            await db.execute("ALTER TABLE links ADD COLUMN user_link_id INTEGER NOT NULL DEFAULT 0")
            # Backfill: assign sequential IDs per user ordered by global id
            await db.execute("""
                UPDATE links SET user_link_id = (
                    SELECT COUNT(*) FROM links l2
                    WHERE l2.user_id = links.user_id AND l2.id <= links.id
                )
            """)

        await db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_link ON links (user_id, user_link_id)"
        )
        await db.commit()


async def get_by_url(url: str, user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM links WHERE url = ? AND user_id = ?", (url, user_id)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_by_id(link_id: int, user_id: int) -> dict | None:
    """link_id is the user-facing user_link_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM links WHERE user_link_id = ? AND user_id = ?", (link_id, user_id)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def save(url: str, original_url: str, title: str, platform: str, tag: str, user_id: int) -> int:
    """Returns the user-facing user_link_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COALESCE(MAX(user_link_id), 0) + 1 FROM links WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            user_link_id = row[0]
        await db.execute(
            """INSERT INTO links (url, original_url, title, platform, tag, user_id, user_link_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (url, original_url, title or "", platform, tag, user_id, user_link_id)
        )
        await db.commit()
        return user_link_id


async def set_tag(link_id: int, tag: str, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE links SET tag = ?, updated_at = CURRENT_TIMESTAMP WHERE user_link_id = ? AND user_id = ?",
            (tag, link_id, user_id)
        )
        await db.commit()


async def set_status(link_id: int, status: str, user_id: int):
    done_at = datetime.utcnow().isoformat() if status == "done" else None
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE links SET status = ?, done_at = ?, updated_at = CURRENT_TIMESTAMP WHERE user_link_id = ? AND user_id = ?",
            (status, done_at, link_id, user_id)
        )
        await db.commit()


async def list_links(user_id: int, tag_prefix: str = None, status_filter: list = None) -> list[dict]:
    if status_filter is None:
        status_filter = ["unread", "pinned", "later"]

    placeholders = ",".join("?" * len(status_filter))
    args = list(status_filter) + [user_id]

    query = f"SELECT * FROM links WHERE status IN ({placeholders}) AND user_id = ?"
    if tag_prefix:
        query += " AND (tag = ? OR tag LIKE ?)"
        args += [tag_prefix, f"{tag_prefix}/%"]

    query += " ORDER BY CASE status WHEN 'pinned' THEN 0 WHEN 'unread' THEN 1 WHEN 'later' THEN 2 END, saved_at DESC, user_link_id DESC"

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, args) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def list_archive(user_id: int, tag_prefix: str = None) -> list[dict]:
    args = [user_id]
    query = "SELECT * FROM links WHERE status = 'done' AND user_id = ?"
    if tag_prefix:
        query += " AND (tag = ? OR tag LIKE ?)"
        args += [tag_prefix, f"{tag_prefix}/%"]
    query += " ORDER BY done_at DESC"

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, args) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def search_links(keyword: str, user_id: int) -> list[dict]:
    kw = f"%{keyword}%"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM links WHERE status != 'done' AND user_id = ? AND (title LIKE ? OR description LIKE ? OR tag LIKE ?) ORDER BY saved_at DESC",
            (user_id, kw, kw, kw)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_all_tags(user_id: int) -> list[tuple[str, int]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT tag, COUNT(*) as cnt FROM links WHERE status != 'done' AND user_id = ? GROUP BY tag ORDER BY cnt DESC",
            (user_id,)
        ) as cur:
            return await cur.fetchall()


async def get_all_active(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM links WHERE status != 'done' AND user_id = ? ORDER BY saved_at DESC",
            (user_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def set_title(link_id: int, title: str, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE links SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE user_link_id = ? AND user_id = ?",
            (title, link_id, user_id)
        )
        await db.commit()


async def delete_link(link_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM links WHERE user_link_id = ? AND user_id = ?", (link_id, user_id)
        )
        await db.commit()


async def retag_links(old_tag: str, new_tag: str, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE links SET tag = ?, updated_at = CURRENT_TIMESTAMP WHERE tag = ? AND user_id = ?",
            (new_tag, old_tag, user_id)
        )
        await db.commit()
