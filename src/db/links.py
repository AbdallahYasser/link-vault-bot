import aiosqlite
from datetime import datetime
from src.config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                url          TEXT UNIQUE NOT NULL,
                original_url TEXT NOT NULL,
                title        TEXT,
                description  TEXT,
                platform     TEXT DEFAULT 'article',
                tag          TEXT DEFAULT 'uncategorized',
                status       TEXT DEFAULT 'unread',
                saved_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                done_at      DATETIME
            )
        """)
        await db.commit()


async def get_by_url(url: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM links WHERE url = ?", (url,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_by_id(link_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM links WHERE id = ?", (link_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def save(url: str, original_url: str, title: str, platform: str, tag: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO links (url, original_url, title, platform, tag)
               VALUES (?, ?, ?, ?, ?)""",
            (url, original_url, title or "", platform, tag)
        )
        await db.commit()
        return cur.lastrowid


async def set_tag(link_id: int, tag: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE links SET tag = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (tag, link_id)
        )
        await db.commit()


async def set_status(link_id: int, status: str):
    done_at = datetime.utcnow().isoformat() if status == "done" else None
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE links SET status = ?, done_at = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, done_at, link_id)
        )
        await db.commit()


async def list_links(tag_prefix: str = None, status_filter: list = None) -> list[dict]:
    if status_filter is None:
        status_filter = ["unread", "pinned", "later"]

    placeholders = ",".join("?" * len(status_filter))
    args = list(status_filter)

    query = f"SELECT * FROM links WHERE status IN ({placeholders})"
    if tag_prefix:
        query += " AND (tag = ? OR tag LIKE ?)"
        args += [tag_prefix, f"{tag_prefix}/%"]

    query += " ORDER BY CASE status WHEN 'pinned' THEN 0 WHEN 'unread' THEN 1 WHEN 'later' THEN 2 END, saved_at DESC, id DESC"

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, args) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def list_archive(tag_prefix: str = None) -> list[dict]:
    args = []
    query = "SELECT * FROM links WHERE status = 'done'"
    if tag_prefix:
        query += " AND (tag = ? OR tag LIKE ?)"
        args += [tag_prefix, f"{tag_prefix}/%"]
    query += " ORDER BY done_at DESC"

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, args) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def search_links(keyword: str) -> list[dict]:
    kw = f"%{keyword}%"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM links WHERE status != 'done' AND (title LIKE ? OR description LIKE ? OR tag LIKE ?) ORDER BY saved_at DESC",
            (kw, kw, kw)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_all_tags() -> list[tuple[str, int]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT tag, COUNT(*) as cnt FROM links WHERE status != 'done' GROUP BY tag ORDER BY cnt DESC"
        ) as cur:
            return await cur.fetchall()


async def get_all_active() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM links WHERE status != 'done' ORDER BY saved_at DESC") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def set_title(link_id: int, title: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE links SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (title, link_id)
        )
        await db.commit()


async def delete_link(link_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM links WHERE id = ?", (link_id,))
        await db.commit()
