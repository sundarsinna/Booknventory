# Book Inventory

A Streamlit application for tracking a personal book collection. It uses
PostgreSQL to store book details, reading status, purchase price, and lending
history.

## Features

- **Dashboard** with counts for all books, read, reading, and unread books, plus
  the total purchase price.
- Dashboard buttons show the corresponding book details on the same page.
- Optional series names are kept separate from book/story titles. For example:
  `DOG MAN` is the series and `Lord of the Fleas` is the book title.
- Optional series emojis are saved with book records and shown in book lists.
- Add and edit book details, including series, title, author, category, volume,
  purchase price, reading status, description, and remarks.
- Search by series name, book/story title, or description, with an optional
  reading-status filter.
- Lend a book to a borrower and record an expected return date; return a lent
  book by its Book ID.
- Bulk import books from CSV or Excel files.
- The app title, navigation labels, book statuses, and purchase-price labels use
  emoji for easier scanning.

Ratings are not currently stored or managed by this application.

## Project files

| File | Purpose |
|---|---|
| `BookInventory.py` | Main Streamlit entry point, navigation, database connection, book forms, search, lending, returns, and imports |
| `api.py` | FastAPI endpoints for creating, updating, and searching books |
| `dashboard.py` | Dashboard metrics and in-page book-detail table |
| `db_config.py` | Reads PostgreSQL connection settings from environment variables |
| `add_series_name.sql` | Adds the optional `series_name` column to an existing `books` table |
| `add_series_emoji.sql` | Adds the optional `series_emoji` column and preserves current DOG MAN/INVESTIGATORS icons |
| `set_default_book_price.sql` | Sets the purchase-price default to zero and repairs existing NULL/NaN prices |
| `requirements.txt` | Python package dependencies |

## Requirements

- Python
- PostgreSQL with the application database and required base tables created
- The Python dependencies listed in `requirements.txt`

The application expects these tables to exist:

- `books`, with the fields used by the app: `book_id`, `series_name`,
  `series_emoji`, `book_name`, `author`, `category`, `volume_no`, `purchase_price`,
  `read_status`, `remarks`, and `updated_at`.
- `borrowers`, with `borrower_id`, `borrower_name`, and `phone`.
- `book_loans`, with `loan_id`, `book_id`, `borrower_id`, `loan_date`,
  `expected_return_date`, `actual_return_date`, and `loan_status`.

The project currently does not include a SQL script that creates these base
tables. The migration scripts below alter an existing `books` table; they do
not initialize a new database.

## Installation

From the project directory, create and activate a virtual environment, then
install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For Excel (`.xlsx`) uploads, install a pandas-compatible Excel reader if one is
not already available:

```bash
pip install openpyxl
```

## Database configuration

`db_config.py` reads database settings from environment variables first, then
from `.streamlit/secrets.toml`, then uses the defaults shown below:

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | PostgreSQL server host |
| `DB_PORT` | `5432` | PostgreSQL server port |
| `DB_NAME` | `postgres` | Database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | Not set | Database password |
| `PGPASSWORD` | Not set | Password fallback if `DB_PASSWORD` is unset |
| `DB_SCHEMA` | `BookInventory` | PostgreSQL schema used by the app |
| `BOOK_API_URL` | `http://127.0.0.1:8002` | Base URL used by Streamlit for the book API |

For local development, store your database settings in
`.streamlit/secrets.toml` at the project root so you do not need to export them
every time. Create the directory if needed:

```bash
mkdir -p .streamlit
```

Add your actual connection values to `.streamlit/secrets.toml`:

```toml
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "your-database-name"
DB_USER = "your-database-user"
DB_PASSWORD = "your-postgres-password"
DB_SCHEMA = "BookInventory"
BOOK_API_URL = "http://127.0.0.1:8002"
```

The secrets file is excluded from Git. Do not commit passwords or other
secrets to this project. Environment variables remain supported and take
precedence over values in the secrets file. The same file is used by both
Streamlit and the FastAPI app.

## Database migrations

Run these migrations against the target database after the `books` table has
been created. The configured schema defaults to the case-sensitive name
`BookInventory`.

For example, from `psql` connected to the application database:

```sql
SET search_path TO "BookInventory";
\i add_series_name.sql
\i add_series_emoji.sql
\i set_default_book_price.sql
```

The series migrations add nullable `series_name` and `series_emoji` columns,
preserving existing book records. The emoji migration carries over the
previously displayed DOG MAN and INVESTIGATORS icons into the new column. The
price migration sets a default of zero and changes existing NULL or PostgreSQL
NaN purchase prices to zero.

## Run the application

Start the API and Streamlit in separate terminals from the project directory,
with the virtual environment activated and database settings configured.

In the first terminal, start the API:

```bash
uvicorn api:app --reload --port 8002
```

In a second terminal, start Streamlit:

```bash
streamlit run BookInventory.py
```

The interactive API documentation is available at
`http://127.0.0.1:8002/docs`.
The book endpoints are:

- `POST /books` — create a book, optionally including its description.
- `PUT /books/{book_id}` — replace a book's editable details, including its
  description and remarks.
- `GET /books/{book_id}` — load a book for the Streamlit Update Book form.
- `GET /books?search=...&status=...&limit=...` — search book title, series, or
  description, with an optional reading-status filter. The limit defaults to
  100 and cannot exceed 500.

The Streamlit Add Book, Update Book, and Search Book pages call this API. Set
`BOOK_API_URL` in `.streamlit/secrets.toml` if the API runs on a different host
or port. Other Streamlit features still connect directly to PostgreSQL.

## How the application works

### Book records

Each row in `books` represents an individual book/volume. The series name is
optional and stored separately from the book/story title. The app checks for
duplicates by series, title, author, and volume number.
The optional series emoji is stored in `series_emoji`; provide the same emoji
when adding each book in that series. Existing series icons can be changed in
Update Book.

Reading status is stored using these values:

- `Unread`
- `Reading`
- `Read`

The UI displays them as ❌ Not Read, ⏳ Reading, and ✅ Read. The emojis are
display labels; they do not replace the database values.

New book forms default the purchase price to zero. Missing or NaN prices are
also treated as zero in the dashboard and are normalized during bulk import.

### Dashboard

The dashboard is implemented in `dashboard.py`; the main app passes it the
database connection function and display helpers. Its metrics include:

- **📚 Books** — all book records.
- **✅ Read**, **⏳ Reading**, and **❌ Not Read** — counts by reading status.
- **💰 Purchase Price** — sum of the purchase prices.

Selecting a metric button stores the selected filter in Streamlit session state
and displays up to 500 matching records below the metrics. The purchase-price
view shows all books, ordered by price descending. Book details are displayed
on the dashboard page; use **Close book details** to hide the table.

The dashboard content uses a bisque background. The application title is
centered above the page navigation.

### Search and update

Search matches a partial series name, book/story title, or description and can
be filtered by reading status. Update Book loads a record by Book ID, displays
its current values, and saves edited fields back to that record.

### Loans

Lending requires a borrower name and an optional phone number containing only
digits, spaces, `+`, or `-`. A book cannot be lent again while an active
`BORROWED` loan exists. Returning a book updates the active loan's actual return
date and status.

### Bulk import

CSV and Excel imports expect these columns:

- `book_name`
- `author`
- `category`
- `volume_no`
- `purchase_price`
- `read_status`

The optional `series_name` and `series_emoji` columns can be used for books in
a series. Use the same `series_emoji` value for every book in a series. Blank
purchase prices are imported as zero. Rows conflicting with a database
uniqueness constraint are skipped with `ON CONFLICT DO NOTHING`.
