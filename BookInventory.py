import streamlit as st
import psycopg2
from psycopg2 import sql
import pandas as pd
import re
import logging
from datetime import date
import db_config
from dashboard import dashboard

DB_PASSWORD = db_config.DB_PASSWORD

# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(
    filename="book_inventory.log",
    level=logging.ERROR,
    format="%(asctime)s %(levelname)s %(message)s"
)

# =====================================================
# DATABASE CONNECTION
# =====================================================

def get_connection():
    if not DB_PASSWORD:
        message = (
            "Database password is not configured. Set DB_PASSWORD (or "
            "PGPASSWORD) in the environment before starting Streamlit."
        )
        st.error(message)
        logging.error(message)
        return None

    try:
        conn = psycopg2.connect(
            host=db_config.DB_HOST,
            port=db_config.DB_PORT,
            database=db_config.DB_NAME,
            user=db_config.DB_USER,
            password=DB_PASSWORD
        )
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SET search_path TO {}").format(
                    sql.Identifier(db_config.DB_SCHEMA)
                )
            )
        return conn

    except Exception as e:
        st.error(f"Database Connection Failed: {e}")
        logging.exception(e)
        return None

# =====================================================
# VALIDATION
# =====================================================

def validate_book(book_name, author, price, series_name=""):

    errors = []

    if not book_name.strip():
        errors.append("Book Name is required")

    if not author.strip():
        errors.append("Author is required")

    if len(book_name) > 255:
        errors.append("Book Name exceeds 255 characters")

    if len(series_name) > 255:
        errors.append("Series Name exceeds 255 characters")

    if price < 0:
        errors.append("Price cannot be negative")

    return errors


def validate_phone(phone):

    if not phone:
        return True

    pattern = r"^[0-9+\- ]+$"

    return bool(re.match(pattern, phone))


def display_read_status(status):
    return {
        "Read": "✅ Read",
        "Reading": "⏳ Reading",
        "Unread": "❌ Not Read",
    }.get(status, status)


def display_series_name(series_name, series_emoji=None):
    if series_name is None or pd.isna(series_name):
        return series_name

    if not str(series_name).strip():
        return series_name

    if series_emoji is None or pd.isna(series_emoji):
        return series_name

    series_emoji = str(series_emoji).strip()
    return f"{series_emoji} {series_name}" if series_emoji else series_name


# =====================================================
# ADD BOOK
# =====================================================

def add_book():

    st.header("➕ Add Book")

    with st.form("book_form"):

        series_name = st.text_input("Series Name (optional)")
        series_emoji = st.text_input(
            "Series Emoji (optional)",
            help="Use the same emoji for every book in this series."
        )
        book_name = st.text_input("📚 Book / Story Name")
        author = st.text_input("Author")
        category = st.text_input("Category")
        volume = st.number_input(
            "Volume",
            min_value=1,
            value=1
        )

        price = st.number_input(
            "💰 Purchase Price",
            min_value=0.0,
            value=0.0
        )

        status = st.selectbox(
            "Status",
            ["Unread", "Reading", "Read"],
            format_func=display_read_status
        )

        submit = st.form_submit_button("Save")

    if submit:

        series_name = series_name.strip()
        series_emoji = series_emoji.strip()

        errors = validate_book(
            book_name,
            author,
            price,
            series_name
        )

        if errors:
            for err in errors:
                st.error(err)
            return

        conn = get_connection()
        if not conn:
            return

        try:

            cur = conn.cursor()

            cur.execute("""
            SELECT COUNT(*)
            FROM books
            WHERE LOWER(COALESCE(series_name, ''))=LOWER(%s)
            AND LOWER(book_name)=LOWER(%s)
            AND LOWER(author)=LOWER(%s)
            AND volume_no=%s
            """,
            (
                series_name,
                book_name,
                author,
                volume
            ))

            exists = cur.fetchone()[0]

            if exists > 0:
                st.warning("Book already exists")
                return

            cur.execute("""
            INSERT INTO books
            (
                series_name,
                series_emoji,
                book_name,
                author,
                category,
                volume_no,
                purchase_price,
                read_status
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                series_name or None,
                series_emoji or None,
                book_name,
                author,
                category,
                volume,
                price,
                status
            ))

            conn.commit()

            st.success(
                "Book Added Successfully"
            )

        except Exception as e:

            conn.rollback()
            st.error(str(e))
            logging.exception(e)

        finally:

            cur.close()
            conn.close()

# =====================================================
# SEARCH BOOKS
# =====================================================

def search_books():

    st.header("🔍 Search Books")

    search_text = st.text_input(
        "📚 Series or Book / Story Name"
    )

    status = st.selectbox(
        "Status",
        ["All", "Unread", "Reading", "Read"],
        format_func=lambda value: (
            "All" if value == "All" else display_read_status(value)
        )
    )

    conn = get_connection()
    if not conn:
        return

    try:

        query = """
        SELECT
            book_id,
            series_name,
            series_emoji,
            book_name,
            author,
            category,
            volume_no,
            purchase_price,
            read_status
        FROM books
        WHERE 1=1
        """

        params = []

        if search_text:

            query += """
            AND (
                LOWER(book_name) LIKE LOWER(%s)
                OR LOWER(COALESCE(series_name, '')) LIKE LOWER(%s)
            )
            """

            search_pattern = f"%{search_text}%"
            params.extend([search_pattern, search_pattern])

        if status != "All":

            query += """
            AND read_status=%s
            """

            params.append(status)

        query += " ORDER BY series_name NULLS FIRST, book_name LIMIT 500"

        df = pd.read_sql(
            query,
            conn,
            params=params
        )

        display_df = df.copy()
        display_df["series_name"] = display_df.apply(
            lambda row: display_series_name(
                row["series_name"],
                row["series_emoji"]
            ),
            axis=1
        )
        display_df = display_df.drop(columns=["series_emoji"])
        display_df["read_status"] = display_df["read_status"].map(
            display_read_status
        )
        st.dataframe(
            display_df,
            use_container_width=True
        )

    except Exception as e:

        st.error(str(e))
        logging.exception(e)

    finally:

        conn.close()

# =====================================================
# UPDATE BOOK
# =====================================================

def update_book():

    st.header("✏ Update Book")

    book_id = st.number_input(
        "Book ID",
        min_value=1
    )

    conn = get_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT
                series_name,
                series_emoji,
                book_name,
                author,
                category,
                volume_no,
                purchase_price,
                read_status,
                remarks
            FROM books
            WHERE book_id=%s
            """, (book_id,))
            book = cur.fetchone()

    except Exception as e:
        st.error(f"Could not load book details: {e}")
        logging.exception(e)
        return

    finally:
        conn.close()

    if not book:
        st.info("Enter an existing Book ID to view and edit its details.")
        return

    (
        current_series,
        current_series_emoji,
        current_title,
        current_author,
        current_category,
        current_volume,
        current_price,
        current_status,
        current_remarks,
    ) = book

    if current_price is None or pd.isna(current_price):
        current_price = 0

    st.caption(f"Editing Book ID {int(book_id)}")

    with st.form(f"update_book_form_{int(book_id)}"):
        series_name = st.text_input(
            "Series Name (optional)",
            value=current_series or "",
            key=f"update_series_{int(book_id)}"
        )
        series_emoji = st.text_input(
            "Series Emoji (optional)",
            value=current_series_emoji or "",
            help="Use the same emoji for every book in this series.",
            key=f"update_series_emoji_{int(book_id)}"
        )
        book_name = st.text_input(
            "📚 Book / Story Name",
            value=current_title or "",
            key=f"update_title_{int(book_id)}"
        )
        author = st.text_input(
            "Author",
            value=current_author or "",
            key=f"update_author_{int(book_id)}"
        )
        category = st.text_input(
            "Category",
            value=current_category or "",
            key=f"update_category_{int(book_id)}"
        )
        volume = st.number_input(
            "Volume",
            min_value=1,
            value=max(1, int(current_volume or 1)),
            key=f"update_volume_{int(book_id)}"
        )
        price = st.number_input(
            "💰 Purchase Price",
            min_value=0.0,
            value=float(current_price or 0),
            key=f"update_price_{int(book_id)}"
        )
        status_options = ["Unread", "Reading", "Read"]
        status_index = (
            status_options.index(current_status)
            if current_status in status_options
            else 0
        )
        status = st.selectbox(
            "Status",
            status_options,
            index=status_index,
            format_func=display_read_status,
            key=f"update_status_{int(book_id)}"
        )
        remarks = st.text_area(
            "Remarks",
            value=current_remarks or "",
            key=f"update_remarks_{int(book_id)}"
        )
        submit = st.form_submit_button("Save Changes")

    if not submit:
        return

    series_name = series_name.strip()
    series_emoji = series_emoji.strip()
    errors = validate_book(book_name, author, price, series_name)
    if errors:
        for error in errors:
            st.error(error)
        return

    conn = get_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cur:
            cur.execute("""
            UPDATE books
            SET
                series_name=%s,
                series_emoji=%s,
                book_name=%s,
                author=%s,
                category=%s,
                volume_no=%s,
                purchase_price=%s,
                read_status=%s,
                remarks=%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE book_id=%s
            """,
            (
                series_name or None,
                series_emoji or None,
                book_name,
                author,
                category,
                volume,
                price,
                status,
                remarks,
                book_id
            ))

            if cur.rowcount == 0:
                st.error("Book ID not found; no changes were saved.")
                return

        conn.commit()
        st.success("Book details updated successfully.")

    except Exception as e:
        conn.rollback()
        st.error(f"Could not update book details: {e}")
        logging.exception(e)

    finally:
        conn.close()

# =====================================================
# LEND BOOK
# =====================================================

def lend_book():

    st.header("📖 Lend Book")

    book_id = st.number_input(
        "Book ID",
        min_value=1
    )

    borrower_name = st.text_input(
        "Borrower Name"
    )

    phone = st.text_input(
        "Phone"
    )

    expected_date = st.date_input(
        "Return Date",
        date.today()
    )

    if st.button("Lend Book"):

        if not borrower_name:
            st.error(
                "Borrower Name required"
            )
            return

        if not validate_phone(phone):

            st.error(
                "Invalid phone number"
            )

            return

        conn = get_connection()
        if not conn:
            return

        try:

            cur = conn.cursor()

            cur.execute("""
            SELECT COUNT(*)
            FROM book_loans
            WHERE book_id=%s
            AND loan_status='BORROWED'
            """,
            (book_id,)
            )

            if cur.fetchone()[0] > 0:

                st.error(
                    "Book already lent"
                )

                return

            cur.execute("""
            INSERT INTO borrowers
            (
                borrower_name,
                phone
            )
            VALUES(%s,%s)
            RETURNING borrower_id
            """,
            (
                borrower_name,
                phone
            ))

            borrower_id = cur.fetchone()[0]

            cur.execute("""
            INSERT INTO book_loans
            (
                book_id,
                borrower_id,
                loan_date,
                expected_return_date,
                loan_status
            )
            VALUES
            (
                %s,
                %s,
                CURRENT_DATE,
                %s,
                'BORROWED'
            )
            """,
            (
                book_id,
                borrower_id,
                expected_date
            ))

            conn.commit()

            st.success(
                "Book Lent Successfully"
            )

        except Exception as e:

            conn.rollback()
            st.error(str(e))
            logging.exception(e)

        finally:

            cur.close()
            conn.close()

# =====================================================
# RETURN BOOK
# =====================================================

def return_book():

    st.header("📚 Return Book")

    book_id = st.number_input(
        "Book ID ",
        min_value=1
    )

    if st.button("Return"):

        conn = get_connection()
        if not conn:
            return

        try:

            cur = conn.cursor()

            cur.execute("""
            UPDATE book_loans
            SET
                actual_return_date=CURRENT_DATE,
                loan_status='RETURNED'
            WHERE loan_id=
            (
                SELECT loan_id
                FROM book_loans
                WHERE book_id=%s
                AND loan_status='BORROWED'
                LIMIT 1
            )
            """,
            (book_id,)
            )

            conn.commit()

            st.success(
                "Book Returned"
            )

        except Exception as e:

            conn.rollback()
            st.error(str(e))
            logging.exception(e)

        finally:

            cur.close()
            conn.close()

# =====================================================
# BULK UPLOAD
# =====================================================

def upload_books():

    st.header("📤 Upload Books")

    uploaded_file = st.file_uploader(
        "Upload CSV/Excel",
        type=["csv", "xlsx"]
    )

    if uploaded_file is None:
        return

    try:

        if uploaded_file.name.endswith(
            ".csv"
        ):

            df = pd.read_csv(
                uploaded_file
            )

        else:

            df = pd.read_excel(
                uploaded_file
            )

        st.dataframe(df.head())

        if st.button("Import Books"):

            conn = get_connection()
            if not conn:
                return

            cur = conn.cursor()

            success = 0

            try:
                for _, row in df.iterrows():
                    series_name = row.get("series_name")
                    if pd.isna(series_name):
                        series_name = None
                    series_emoji = row.get("series_emoji")
                    if pd.isna(series_emoji):
                        series_emoji = None
                    purchase_price = row.get("purchase_price", 0)
                    if pd.isna(purchase_price):
                        purchase_price = 0

                    cur.execute("""
                    INSERT INTO books
                    (
                        series_name,
                        series_emoji,
                        book_name,
                        author,
                        category,
                        volume_no,
                        purchase_price,
                        read_status
                    )
                    VALUES
                    (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        series_name,
                        series_emoji,
                        row["book_name"],
                        row["author"],
                        row["category"],
                        row["volume_no"],
                        purchase_price,
                        row["read_status"]
                    ))

                    success += cur.rowcount

                conn.commit()
                st.success(
                    f"{success} books imported"
                )

            except Exception as e:
                conn.rollback()
                st.error(f"Book import failed: {e}")
                logging.exception(e)

            finally:
                cur.close()
                conn.close()

    except Exception as e:

        st.error(str(e))
        logging.exception(e)

# =====================================================
# MAIN
# =====================================================

st.set_page_config(
    page_title="Book Inventory System",
    layout="wide"
)

st.markdown(
    "<h1 style='text-align: center;'>📚 Book Inventory System</h1>",
    unsafe_allow_html=True
)


menu = st.sidebar.selectbox(
    "📚 Menu",
    [
        "📊 Dashboard",
        "➕ Add Book",
        "🔍 Search Book",
        "✏️ Update Book",
        "📤 Lend Book",
        "📥 Return Book",
        "⬆️ Upload Books"
    ]
)

if menu == "📊 Dashboard":
    dashboard(get_connection, display_read_status, display_series_name)

elif menu == "➕ Add Book":
    add_book()

elif menu == "🔍 Search Book":
    search_books()

elif menu == "✏️ Update Book":
    update_book()

elif menu == "📤 Lend Book":
    lend_book()

elif menu == "📥 Return Book":
    return_book()

elif menu == "⬆️ Upload Books":
    upload_books()