import sqlite3
import pandas as pd

DB_NAME = "invoices.db"


# -------------------------------
# DATABASE CONNECTION
# -------------------------------
def get_connection():
    return sqlite3.connect(DB_NAME)


# -------------------------------
# CREATE TABLE
# -------------------------------
def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        store_name TEXT,
        invoice_no TEXT UNIQUE,
        date TEXT,
        total REAL,
        raw_text TEXT,
        file_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


# -------------------------------
# CHECK DUPLICATE INVOICE
# -------------------------------
def check_invoice_exists(invoice_no):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT 1 FROM invoices WHERE invoice_no = ?",
        (invoice_no,)
    )

    exists = cur.fetchone() is not None
    conn.close()
    return exists


# -------------------------------
# SAVE INVOICE
# -------------------------------
def save_invoice(structured_data, ocr_text, file_path):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO invoices (
            store_name, invoice_no, date, total, raw_text, file_path
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        structured_data["store_name"],
        structured_data["invoice_no"],
        structured_data["date"],
        structured_data["total"],
        ocr_text,
        file_path
    ))

    conn.commit()
    conn.close()


# -------------------------------
# FETCH ALL INVOICES
# -------------------------------
def fetch_all_invoices():
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT store_name, invoice_no, date, total
        FROM invoices
        ORDER BY created_at DESC
        """,
        conn
    )
    conn.close()
    return df
