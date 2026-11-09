import logging
from decimal import Decimal
from typing import Literal

import psycopg2
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

import db_config


logger = logging.getLogger(__name__)
app = FastAPI(title="Book Inventory API")

ReadStatus = Literal["Unread", "Reading", "Read"]
BookStatusFilter = Literal["All", "Unread", "Reading", "Read"]
BOOK_COLUMNS = """
    book_id,
    series_name,
    series_emoji,
    book_name,
    author,
    category,
    volume_no,
    purchase_price,
    read_status,
    description,
    remarks
"""


class BookFields(BaseModel):
    series_name: str | None = Field(...)
    series_emoji: str | None = Field(...)
    book_name: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    category: str | None = Field(..., max_length=100)
    volume_no: int = Field(ge=1)
    purchase_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    read_status: ReadStatus
    description: str | None = Field(..., max_length=250)

    @field_validator("book_name", "author")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("series_name", "series_emoji", "category", "description")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class BookCreate(BookFields):
    series_name: str | None = None
    series_emoji: str | None = None
    category: str | None = None
    volume_no: int = Field(default=1, ge=1)
    purchase_price: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    read_status: ReadStatus = "Unread"
    description: str | None = Field(default=None, max_length=250)


class BookUpdate(BookFields):
    remarks: str | None = None

    @field_validator("remarks")
    @classmethod
    def normalize_remarks(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class BookResponse(BaseModel):
    book_id: int
    series_name: str | None
    series_emoji: str | None
    book_name: str
    author: str
    category: str | None
    volume_no: int | None
    purchase_price: Decimal | None
    read_status: str | None
    description: str | None
    remarks: str | None


def get_db_connection():
    if not db_config.DB_PASSWORD:
        raise HTTPException(
            status_code=503,
            detail="Database password is not configured.",
        )

    conn = None
    try:
        conn = psycopg2.connect(
            host=db_config.DB_HOST,
            port=db_config.DB_PORT,
            database=db_config.DB_NAME,
            user=db_config.DB_USER,
            password=db_config.DB_PASSWORD,
        )
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SET search_path TO {}").format(
                    sql.Identifier(db_config.DB_SCHEMA)
                )
            )
        return conn
    except psycopg2.Error as exc:
        if conn is not None:
            conn.close()
        logger.exception("Could not connect to the database")
        raise HTTPException(
            status_code=503,
            detail="Could not connect to the database.",
        ) from exc


def raise_database_error(exc: psycopg2.Error) -> None:
    logger.exception("Book database operation failed", exc_info=exc)
    raise HTTPException(
        status_code=500,
        detail="Book database operation failed.",
    ) from exc


@app.post("/books", response_model=BookResponse, status_code=201)
def add_book(book: BookCreate) -> BookResponse:
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT 1
                    FROM books
                    WHERE LOWER(COALESCE(series_name, '')) = LOWER(%s)
                      AND LOWER(book_name) = LOWER(%s)
                      AND LOWER(author) = LOWER(%s)
                      AND volume_no = %s
                    LIMIT 1
                    """,
                    (
                        book.series_name or "",
                        book.book_name,
                        book.author,
                        book.volume_no,
                    ),
                )
                if cur.fetchone():
                    raise HTTPException(
                        status_code=409,
                        detail="Book already exists.",
                    )

                cur.execute(
                    f"""
                    INSERT INTO books (
                        series_name,
                        series_emoji,
                        book_name,
                        author,
                        category,
                        volume_no,
                        purchase_price,
                        read_status,
                        description
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING {BOOK_COLUMNS}
                    """,
                    (
                        book.series_name,
                        book.series_emoji,
                        book.book_name,
                        book.author,
                        book.category,
                        book.volume_no,
                        book.purchase_price,
                        book.read_status,
                        book.description,
                    ),
                )
                created_book = cur.fetchone()
        return BookResponse(**created_book)
    except HTTPException:
        raise
    except psycopg2.Error as exc:
        raise_database_error(exc)
    finally:
        conn.close()


@app.put("/books/{book_id}", response_model=BookResponse)
def update_book(book_id: int, book: BookUpdate) -> BookResponse:
    if book_id < 1:
        raise HTTPException(status_code=422, detail="Book ID must be positive.")

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT 1 FROM books WHERE book_id = %s",
                    (book_id,),
                )
                if cur.fetchone() is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Book ID not found.",
                    )

                cur.execute(
                    """
                    SELECT 1
                    FROM books
                    WHERE book_id <> %s
                      AND LOWER(COALESCE(series_name, '')) = LOWER(%s)
                      AND LOWER(book_name) = LOWER(%s)
                      AND LOWER(author) = LOWER(%s)
                      AND volume_no = %s
                    LIMIT 1
                    """,
                    (
                        book_id,
                        book.series_name or "",
                        book.book_name,
                        book.author,
                        book.volume_no,
                    ),
                )
                if cur.fetchone():
                    raise HTTPException(
                        status_code=409,
                        detail="Another book already has these details.",
                    )

                cur.execute(
                    f"""
                    UPDATE books
                    SET
                        series_name = %s,
                        series_emoji = %s,
                        book_name = %s,
                        author = %s,
                        category = %s,
                        volume_no = %s,
                        purchase_price = %s,
                        read_status = %s,
                        description = %s,
                        remarks = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE book_id = %s
                    RETURNING {BOOK_COLUMNS}
                    """,
                    (
                        book.series_name,
                        book.series_emoji,
                        book.book_name,
                        book.author,
                        book.category,
                        book.volume_no,
                        book.purchase_price,
                        book.read_status,
                        book.description,
                        book.remarks,
                        book_id,
                    ),
                )
                updated_book = cur.fetchone()
                if updated_book is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Book ID not found.",
                    )
        return BookResponse(**updated_book)
    except HTTPException:
        raise
    except psycopg2.Error as exc:
        raise_database_error(exc)
    finally:
        conn.close()


@app.get("/books/{book_id}", response_model=BookResponse)
def get_book(book_id: int) -> BookResponse:
    if book_id < 1:
        raise HTTPException(status_code=422, detail="Book ID must be positive.")

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"SELECT {BOOK_COLUMNS} FROM books WHERE book_id = %s",
                (book_id,),
            )
            book = cur.fetchone()
        if book is None:
            raise HTTPException(status_code=404, detail="Book ID not found.")
        return BookResponse(**book)
    except psycopg2.Error as exc:
        raise_database_error(exc)
    finally:
        conn.close()


@app.get("/books", response_model=list[BookResponse])
def search_books(
    search: str | None = Query(default=None, description="Match title, series, or description."),
    status: BookStatusFilter = "All",
    limit: int = Query(default=100, ge=1, le=500),
) -> list[BookResponse]:
    conn = get_db_connection()
    try:
        query = f"SELECT {BOOK_COLUMNS} FROM books WHERE 1=1"
        params: list[object] = []

        if search and search.strip():
            query += """
                AND (
                    book_name ILIKE %s
                    OR COALESCE(series_name, '') ILIKE %s
                    OR COALESCE(description, '') ILIKE %s
                )
            """
            pattern = f"%{search.strip()}%"
            params.extend([pattern, pattern, pattern])

        if status != "All":
            query += " AND read_status = %s"
            params.append(status)

        query += " ORDER BY series_name NULLS FIRST, book_name LIMIT %s"
        params.append(limit)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
        return [BookResponse(**row) for row in rows]
    except psycopg2.Error as exc:
        raise_database_error(exc)
    finally:
        conn.close()
