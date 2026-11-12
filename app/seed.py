"""Demo data seeding.

Startup (`seed_demo_user` in lifespan) only creates the admin when `users` is empty.

Richer sample users + books are opt-in via:

    python -m app.seed
    make seed
"""

from __future__ import annotations

import asyncio

from app.auth.passwords import hash_password
from app.auth.seed import seed_demo_user
from app.auth.users import create_user, get_user_by_username
from app.core import config
from app.db import books as books_repo
from app.db.books import BOOK_CATEGORIES
from app.db.connection import close_sqlite, connect_to_sqlite, get_connection

# Shared password for sample non-admin accounts (documented in README).
SAMPLE_PASSWORD = "demo123"

SAMPLE_USERS: list[tuple[str, str, str]] = [
    ("viewer", SAMPLE_PASSWORD, "viewer"),
    ("editor", SAMPLE_PASSWORD, "editor"),
]

# More than the UI default page size (10) so pagination is obvious (~3 pages).
SAMPLE_BOOKS: list[dict[str, object]] = [
    {
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "year": 1813,
        "notes": "Classic novel of manners.",
    },
    {
        "title": "The Hobbit",
        "author": "J. R. R. Tolkien",
        "year": 1937,
        "notes": "There and back again.",
    },
    {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "notes": "Desert planet politics and spice.",
    },
    {
        "title": "Neuromancer",
        "author": "William Gibson",
        "year": 1984,
        "notes": "Cyberpunk cornerstone.",
    },
    {
        "title": "The Left Hand of Darkness",
        "author": "Ursula K. Le Guin",
        "year": 1969,
        "notes": "Ambassador on a winter world.",
    },
    {
        "title": "Kindred",
        "author": "Octavia E. Butler",
        "year": 1979,
        "notes": "Time travel and American history.",
    },
    {
        "title": "The Name of the Rose",
        "author": "Umberto Eco",
        "year": 1980,
        "notes": "Monastery mystery.",
    },
    {
        "title": "Invisible Cities",
        "author": "Italo Calvino",
        "year": 1972,
        "notes": "Marco Polo describes cities to Kublai Khan.",
    },
    {
        "title": "Frankenstein",
        "author": "Mary Shelley",
        "year": 1818,
        "notes": "Creature and creator.",
    },
    {
        "title": "Dracula",
        "author": "Bram Stoker",
        "year": 1897,
        "notes": "Epistolary vampire novel.",
    },
    {
        "title": "Moby-Dick",
        "author": "Herman Melville",
        "year": 1851,
        "notes": "Obsession at sea.",
    },
    {
        "title": "Jane Eyre",
        "author": "Charlotte Brontë",
        "year": 1847,
        "notes": "Gothic bildungsroman.",
    },
    {
        "title": "Wuthering Heights",
        "author": "Emily Brontë",
        "year": 1847,
        "notes": "Stormy moorland passions.",
    },
    {
        "title": "1984",
        "author": "George Orwell",
        "year": 1949,
        "notes": "Surveillance and Newspeak.",
    },
    {
        "title": "Brave New World",
        "author": "Aldous Huxley",
        "year": 1932,
        "notes": "Engineered happiness.",
    },
    {
        "title": "Fahrenheit 451",
        "author": "Ray Bradbury",
        "year": 1953,
        "notes": "Firemen who burn books.",
    },
    {
        "title": "The Handmaid's Tale",
        "author": "Margaret Atwood",
        "year": 1985,
        "notes": "Gilead and resistance.",
    },
    {
        "title": "Beloved",
        "author": "Toni Morrison",
        "year": 1987,
        "notes": "Memory and haunting.",
    },
    {
        "title": "One Hundred Years of Solitude",
        "author": "Gabriel García Márquez",
        "year": 1967,
        "notes": "Macondo across generations.",
    },
    {
        "title": "The Stranger",
        "author": "Albert Camus",
        "year": 1942,
        "notes": "Absurdity in Algiers.",
    },
    {
        "title": "Crime and Punishment",
        "author": "Fyodor Dostoevsky",
        "year": 1866,
        "notes": "Guilt after a crime.",
    },
    {
        "title": "The Trial",
        "author": "Franz Kafka",
        "year": 1925,
        "notes": "Arrested without knowing why.",
    },
    {
        "title": "To Kill a Mockingbird",
        "author": "Harper Lee",
        "year": 1960,
        "notes": "Justice in Maycomb.",
    },
    {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "notes": "Jazz Age longing.",
    },
    {
        "title": "Mrs Dalloway",
        "author": "Virginia Woolf",
        "year": 1925,
        "notes": "One day in London.",
    },
    {
        "title": "Things Fall Apart",
        "author": "Chinua Achebe",
        "year": 1958,
        "notes": "Igbo life and colonial rupture.",
    },
    {
        "title": "The Dispossessed",
        "author": "Ursula K. Le Guin",
        "year": 1974,
        "notes": "Anarres and Urras.",
    },
    {
        "title": "Hyperion",
        "author": "Dan Simmons",
        "year": 1989,
        "notes": "Pilgrims to the Time Tombs.",
    },
]

async def seed_sample_users() -> list[str]:
    """Create sample role users if missing. Returns usernames created."""
    created: list[str] = []
    for username, password, role in SAMPLE_USERS:
        if await get_user_by_username(username) is not None:
            continue
        await create_user(username, hash_password(password), role=role)
        created.append(username)
    return created


_CATEGORY_CYCLE = sorted(BOOK_CATEGORIES)


def _sample_meta(index: int, book: dict[str, object]) -> dict[str, object]:
    """Fill category / ISBN / pages / availability for demo variety."""
    return {
        **book,
        "category": _CATEGORY_CYCLE[index % len(_CATEGORY_CYCLE)],
        "isbn": f"978-{1000000000 + index:010d}",
        "page_count": 180 + (index * 37) % 700,
        "available": index % 5 != 0,
    }


async def _book_id_by_title(title: str) -> str | None:
    conn = get_connection()
    async with conn.execute(
        "SELECT id, isbn FROM books WHERE title = ? LIMIT 1",
        (title,),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return None
    return row["id"]


async def _book_needs_enrichment(book_id: str) -> bool:
    conn = get_connection()
    async with conn.execute(
        "SELECT isbn, added_by_user_id FROM books WHERE id = ?",
        (book_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return False
    return row["isbn"] is None or row["added_by_user_id"] is None


async def seed_sample_books() -> tuple[int, int]:
    """Insert or enrich sample books. Returns (created, enriched)."""
    admin = await get_user_by_username(config.DEMO_USERNAME)
    editor = await get_user_by_username("editor")
    adder_ids = [u["id"] for u in (admin, editor) if u is not None]

    created = 0
    enriched = 0
    for index, raw in enumerate(SAMPLE_BOOKS):
        book = _sample_meta(index, raw)
        title = str(book["title"])
        adder = adder_ids[index % len(adder_ids)] if adder_ids else None
        book_id = await _book_id_by_title(title)

        if book_id is None:
            await books_repo.create_book(
                title=title,
                author=str(book["author"]),
                year=book["year"] if book["year"] is not None else None,  # type: ignore[arg-type]
                notes=str(book["notes"]) if book.get("notes") else None,
                category=str(book["category"]),
                isbn=str(book["isbn"]),
                page_count=int(book["page_count"]),  # type: ignore[arg-type]
                available=bool(book["available"]),
                added_by_user_id=adder,
            )
            created += 1
            continue

        if await _book_needs_enrichment(book_id):
            conn = get_connection()
            await conn.execute(
                """
                UPDATE books
                SET category = ?, isbn = ?, page_count = ?, available = ?,
                    added_by_user_id = COALESCE(added_by_user_id, ?)
                WHERE id = ?
                """,
                (
                    str(book["category"]),
                    str(book["isbn"]),
                    int(book["page_count"]),  # type: ignore[arg-type]
                    1 if book["available"] else 0,
                    adder,
                    book_id,
                ),
            )
            await conn.commit()
            enriched += 1

    return created, enriched


async def run_seed() -> None:
    """Connect, ensure demo admin, add sample users/books (idempotent), disconnect."""
    await connect_to_sqlite()
    try:
        await seed_demo_user()
        created_users = await seed_sample_users()
        books_created, books_enriched = await seed_sample_books()

        if created_users:
            print(
                f"✅ Seeded users: {', '.join(created_users)} "
                "(password: see README)"
            )
        else:
            print("ℹ️  Sample users already present (viewer, editor)")

        if books_created or books_enriched:
            print(
                f"✅ Books seed: {books_created} created, {books_enriched} enriched "
                f"({len(SAMPLE_BOOKS)} samples; UI page size is 10)"
            )
        else:
            print("ℹ️  All sample books already present with metadata")
    finally:
        await close_sqlite()


def main() -> None:
    asyncio.run(run_seed())


if __name__ == "__main__":
    main()
