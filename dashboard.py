import logging

import pandas as pd
import streamlit as st


def dashboard(get_connection, display_read_status, display_series_name):
    st.markdown(
        """
        <style>
        div.st-key-dashboard_background {
            background-color: bisque;
            padding: 1.25rem;
            border-radius: 0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    with st.container(key="dashboard_background"):
        st.header("📊 Dashboard")

        conn = get_connection()
        if not conn:
            return

        try:
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) FROM books")
            total_books = cur.fetchone()[0]

            cur.execute("""
            SELECT COUNT(*)
            FROM books
            WHERE read_status='Read'
            """)
            read_books = cur.fetchone()[0]

            cur.execute("""
            SELECT COUNT(*)
            FROM books
            WHERE read_status='Unread'
            """)
            unread_books = cur.fetchone()[0]

            cur.execute("""
            SELECT COUNT(*)
            FROM books
            WHERE read_status='Reading'
            """)
            reading_books = cur.fetchone()[0]

            cur.execute("""
            SELECT COALESCE(SUM(
                CASE
                    WHEN purchase_price IS NULL
                        OR purchase_price::text IN ('NaN', 'nan', '-NaN')
                    THEN 0
                    ELSE purchase_price
                END
            ),0)
            FROM books
            """)
            total_value = cur.fetchone()[0]
            if total_value is None or pd.isna(total_value):
                total_value = 0

            col1, col2, col3, col4, col5 = st.columns(5)

            dashboard_links = [
                (col1, "📚 Books", total_books, "all"),
                (col2, "✅ Read", read_books, "Read"),
                (col3, "⏳ Reading", reading_books, "Reading"),
                (col4, "❌ Not Read", unread_books, "Unread"),
                (col5, "💰 Purchase Price", f"${total_value}", "purchase_price"),
            ]
            for column, label, value, filter_value in dashboard_links:
                if column.button(label, key=f"dashboard_{filter_value}"):
                    st.session_state["dashboard_filter"] = filter_value
                column.metric(label, value)

            selected_filter = st.session_state.get("dashboard_filter")
            allowed_filters = {
                "all", "Read", "Reading", "Unread", "purchase_price"
            }

            if selected_filter in allowed_filters:
                filter_labels = {
                    "all": "All Books",
                    "Read": "✅ Read Books",
                    "Reading": "⏳ Reading Books",
                    "Unread": "❌ Not Read Books",
                    "purchase_price": "Books and Purchase Prices",
                }
                st.subheader(filter_labels[selected_filter])

                details_query = """
                SELECT
                    book_id,
                    series_name,
                    series_emoji,
                    book_name,
                    author,
                    category,
                    volume_no,
                    CASE
                        WHEN purchase_price IS NULL
                            OR purchase_price::text IN ('NaN', 'nan', '-NaN')
                        THEN 0
                        ELSE purchase_price
                    END AS purchase_price,
                    read_status,
                    remarks
                FROM books
                """
                query_params = []

                if selected_filter in {"Read", "Reading", "Unread"}:
                    details_query += " WHERE read_status=%s"
                    query_params.append(selected_filter)

                if selected_filter == "purchase_price":
                    details_query += """
                    ORDER BY
                        CASE
                            WHEN purchase_price IS NULL
                                OR purchase_price::text IN ('NaN', 'nan', '-NaN')
                            THEN 0
                            ELSE purchase_price
                        END DESC,
                        book_id
                    """
                else:
                    details_query += (
                        " ORDER BY series_name NULLS FIRST, book_name"
                    )

                details_query += " LIMIT 500"
                books_df = pd.read_sql(
                    details_query,
                    conn,
                    params=query_params
                )
                books_df["series_name"] = books_df.apply(
                    lambda row: display_series_name(
                        row["series_name"],
                        row["series_emoji"]
                    ),
                    axis=1
                )
                books_df = books_df.drop(columns=["series_emoji"])
                books_df["read_status"] = books_df["read_status"].map(
                    display_read_status
                )
                st.dataframe(books_df, use_container_width=True)
                st.caption("Showing up to 500 books.")
                if st.button("Close book details", key="close_dashboard_details"):
                    st.session_state.pop("dashboard_filter", None)
                    st.rerun()

        except Exception as e:
            st.error(str(e))
            logging.exception(e)

        finally:
            cur.close()
            conn.close()
