import streamlit as st
import cv2
import numpy as np
import pytesseract
import os
import uuid
import re
from pdf2image import convert_from_path

# Database functions
from database import (
    create_tables,
    save_invoice,
    fetch_all_invoices,
    check_invoice_exists
)

# -------------------------------
# INITIAL SETUP
# -------------------------------
create_tables()

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"D:\Infosys Internship\receipt_invoice_digitizer\bills_invoices\poppler-25.12.0\Library\bin"

st.set_page_config(page_title="Receipt & Invoice Digitizer", layout="wide")
st.title("🧾 Receipt & Invoice Digitizer")
st.subheader("Milestone 1")

# -------------------------------
# SESSION STATE
# -------------------------------
if "invoice_saved" not in st.session_state:
    st.session_state.invoice_saved = False

# -------------------------------
# UPLOAD DIRECTORY
# -------------------------------
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -------------------------------
# IMAGE PREPROCESSING
# -------------------------------
def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)

    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        10
    )
    return thresh

# -------------------------------
# OCR FUNCTION (OPTIMIZED)
# -------------------------------
def extract_text(img):
    custom_config = (
        "--oem 3 "
        "--psm 6 "
        "-c tessedit_char_whitelist="
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789:-/#"
    )
    return pytesseract.image_to_string(img, config=custom_config)
# -------------------------------
# STRUCTURE INVOICE DATA
# -------------------------------
def structure_invoice_text(text):
    structured = {}

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    structured["store_name"] = lines[0] if lines else "N/A"

    # Invoice Number (NUMBERS ONLY)
    invoice_match = re.search(
        r"Invoice\s*(No|Number|#)?\s*[:\-]?\s*([0-9]{3,})",
        text,
        re.I
    )
    structured["invoice_no"] = invoice_match.group(2) if invoice_match else "N/A"

    # Date
    date_match = re.search(
        r"(Date|Dated)\s*[:\-]?\s*([0-9]{2}[\/\-][0-9]{2}[\/\-][0-9]{4})",
        text,
        re.I
    )
    structured["date"] = date_match.group(2) if date_match else "N/A"

    # Total Amount
    total_match = re.search(
        r"(Total|Grand Total|Amount)\s*[=:]?\s*₹?\s*([\d,]+\.\d{2})",
        text,
        re.I
    )
    structured["total"] = total_match.group(2) if total_match else "N/A"

    return structured

# -------------------------------
# FILE UPLOADER
# -------------------------------
uploaded_file = st.file_uploader(
    "Upload Receipt / Invoice (JPG, PNG, PDF)",
    type=["jpg", "jpeg", "png", "pdf"]
)

# -------------------------------
# MAIN LOGIC
# -------------------------------
if uploaded_file is not None:

    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{uploaded_file.name}")

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success("✅ File uploaded successfully")

    all_text = ""

    # -------- IMAGE FILE --------
    if uploaded_file.type != "application/pdf":
        img = cv2.imread(file_path)

        if img is None:
            st.error("❌ Unable to read image file")
            st.stop()

        thresh = preprocess_image(img)
        all_text = extract_text(thresh)

        col1, col2 = st.columns(2)
        with col1:
            st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), caption="Original Image", width=350)
        with col2:
            st.image(thresh, caption="Preprocessed Image", width=350)

    # -------- PDF FILE --------
    else:
        pages = convert_from_path(file_path, dpi=300, poppler_path=POPPLER_PATH)

        for i, page in enumerate(pages):
            img = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
            thresh = preprocess_image(img)
            all_text += extract_text(thresh) + "\n"

            st.markdown(f"### 📄 PDF Page {i + 1}")
            col1, col2 = st.columns(2)
            with col1:
                st.image(page, caption="Original Page", width=350)
            with col2:
                st.image(thresh, caption="Preprocessed Page", width=350)

    # -------------------------------
    # STRUCTURED DATA
    # -------------------------------
    structured_data = structure_invoice_text(all_text)

    st.subheader("📋 Structured Invoice Data")
    st.json(structured_data)

    # -------------------------------
    # SAVE BUTTON
    # -------------------------------
    if st.button("💾 Save Invoice"):
        existing = check_invoice_exists(structured_data["invoice_no"])

        if existing:
            st.warning("⚠️ Invoice already exists. Duplicate not allowed.")
            st.session_state.invoice_saved = True  # still show DB
        else:
            save_invoice(structured_data, all_text, file_path)
            st.success("✅ Invoice saved successfully")
            st.session_state.invoice_saved = True

        st.subheader("📄 Raw OCR Text")
        st.text_area("OCR Output", all_text, height=220)

# -------------------------------
# SHOW DATABASE (AFTER SAVE / DUPLICATE)
# -------------------------------
if st.session_state.invoice_saved:
    st.subheader("📦 Persistent Storage (SQLite Database)")

    df = fetch_all_invoices()

    if df.empty:
        st.info("No invoices saved yet.")
    else:
        st.dataframe(df, use_container_width=True)
