import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, date
from PIL import Image

# 1. Page Settings
st.set_page_config(
    page_title="Equipment Register DB",
    page_icon="🧗",
    layout="wide"
)

# Using absolute paths to ensure the app finds files accurately on the Streamlit Cloud Linux container
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "equipment_inventory.db")
LOGO_FILE = os.path.join(BASE_DIR, "logo.png")

# 2. Database Management
def init_db():
    """Initializes the database tables and handles column migrations on the cloud filesystem."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Equipment Register Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS register (
            sn INTEGER PRIMARY KEY AUTOINCREMENT,
            item_code TEXT NOT NULL,
            manufacture TEXT,
            product TEXT,
            date_of_purchase TEXT,
            equipment_name TEXT,
            standard TEXT,
            year_of_manufacture INTEGER,
            doc_del TEXT,
            supplier TEXT,
            date_of_first_used TEXT,
            date_of_last_used TEXT,
            inspection_date TEXT,
            next_inspection_date TEXT,
            inspected_by TEXT,
            comment TEXT
        )
    ''')
    
    # Metadata Config Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS meta_config (
            id INTEGER PRIMARY KEY DEFAULT 1,
            doc_ref TEXT,
            doc_date TEXT,
            revision TEXT,
            compiled_by TEXT
        )
    ''')
    
    # Seed initial metadata default values if table is completely empty
    c.execute("SELECT COUNT(*) FROM meta_config")
    if c.fetchone()[0] == 0:
        c.execute('''
            INSERT INTO meta_config (id, doc_ref, doc_date, revision, compiled_by)
            VALUES (1, 'REG - 3', '2023-01-28', '1', 'Mirajan Gurung')
        ''')
    
    # --- MIGRATION HANDLING ---
    c.execute("PRAGMA table_info(register)")
    columns = [col[1] for col in c.fetchall()]
    
    if "date_of_purchase" not in columns:
        c.execute("ALTER TABLE register ADD COLUMN date_of_purchase TEXT")
    if "manufacturer" in columns and "manufacture" not in columns:
        c.execute("ALTER TABLE register ADD COLUMN manufacture TEXT")
        c.execute("UPDATE register SET manufacture = manufacturer")
    if "standardd" in columns and "standard" not in columns:
        c.execute("ALTER TABLE register ADD COLUMN standard TEXT")
        c.execute("UPDATE register SET standard = standardd")
    if "equipment_name" not in columns:
        c.execute("ALTER TABLE register ADD COLUMN equipment_name TEXT")
        
    conn.commit()
    conn.close()

def load_data():
    """Loads database records directly into a Pandas DataFrame."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("""
        SELECT 
            sn, item_code, manufacture, product, date_of_purchase, equipment_name, standard, 
            year_of_manufacture, doc_del, supplier, date_of_first_used, 
            date_of_last_used, inspection_date, next_inspection_date, 
            inspected_by, comment 
        FROM register
    """, conn)
    conn.close()
    return df

def load_meta():
    """Loads document header configuration values from DB."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT doc_ref, doc_date, revision, compiled_by FROM meta_config WHERE id = 1")
    res = c.fetchone()
    conn.close()
    return res if res else ('REG - 3', '2023-01-28', '1', 'Mirajan Gurung')

# Initialize database structural setup
init_db()

# Load Current Header Metadata from SQLite
doc_ref, doc_date_str, revision, compiled_by = load_meta()
try:
    parsed_date = datetime.strptime(doc_date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
except Exception:
    parsed_date = doc_date_str

# ========================================================
# LOGO & INLINE EDITABLE HEADER PARAMETERS FORM
# ========================================================
logo_col, title_col = st.columns([1, 4])

with logo_col:
    if os.path.exists(LOGO_FILE):
        try:
            logo_img = Image.open(LOGO_FILE)
            st.image(logo_img, use_container_width=True)
        except Exception:
            st.warning("⚠️ Logo file found but could not be loaded.")
    else:
        st.info("ℹ️ Place 'logo.png' in repository to show image.")

with title_col:
    st.title("🛡️ Equipment Register Database — AIMS NEPAL")
    
    with st.expander("📝 Edit Header Information Fields Inline", expanded=False):
        with st.form(key="inline_header_form"):
            h_col1, h_col2, h_col3, h_col4 = st.columns(4)
            with h_col1:
                new_doc_ref = st.text_input("DOC REFERENCE", value=doc_ref)
            with h_col2:
                try:
                    default_date_obj = datetime.strptime(doc_date_str, "%Y-%m-%d").date()
                except Exception:
                    default_date_obj = date.today()
                new_doc_date = st.date_input("DOCUMENT DATE", value=default_date_obj)
            with h_col3:
                new_revision = st.text_input("REVISION CODE", value=revision)
            with h_col4:
                new_compiled_by = st.text_input("COMPILED BY", value=compiled_by)
                
            save_meta_btn = st.form_submit_button("Update Header Parameters", type="primary")
            
            if save_meta_btn:
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('''
                    UPDATE meta_config 
                    SET doc_ref = ?, doc_date = ?, revision = ?, compiled_by = ?
                    WHERE id = 1
                ''', (new_doc_ref, str(new_doc_date), new_revision, new_compiled_by))
                conn.commit()
                conn.close()
                st.success("Header metrics successfully refreshed!")
                st.rerun()

    st.markdown(
        f"""
        **Doc Ref:** `{doc_ref}` | **Date:** `{parsed_date}` | **Revision:** `{revision}` | **Compiled By:** `{compiled_by}`
        \n*Track gear inspections, manufacture dates, and usage lifecycles reliably.*
        """
    )

st.markdown("---")

# Dropdown Constraints
MANUFACTURE_OPTIONS = ["PETZL", "CAMP", "BLACK DIAMOND", "BEAL", "SPARROW"]
SUPPLIER_OPTIONS = ["ABARIS UK", "PEAK PROMOTION"]
INSPECTED_BY_OPTIONS = ["BHIM B.GURUNG"]

def parse_db_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None

# Tabs Setup
tab_view, tab_add = st.tabs(["📋 View & Filter Register", "➕ Add New Record"])

# ==========================================
# TAB 2: ADD NEW DATA ENTRY RECORD
# ==========================================
with tab_add:
    st.subheader("Register New Equipment Asset")
    
    with st.form(key="equipment_entry_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            item_code = st.text_input("ITEM CODE*", help="Required: Unique identifier or model reference")
            manufacture = st.selectbox("MANUFACTURE", options=[""] + MANUFACTURE_OPTIONS)
            product = st.text_input("PRODUCT", help="e.g., Harness, Carabiner, Dynamic Rope")
            date_of_purchase = st.date_input("DATE OF PURCHASE", value=None)
            
        with col2:
            equipment_name = st.text_input("EQUIPMENT NAME", help="e.g., Avao Bod Croll Fast, Grigri")
            standard = st.text_input("STANDARD", help="e.g., EN 361, EN 12275")
            current_year = datetime.now().year
            year_of_manufacture = st.number_input("YEAR OF MANUFACTURE", min_value=1990, max_value=current_year + 5, value=current_year)
            doc_del = st.text_input("DOC/DEL")

        with col3:
            supplier = st.selectbox("SUPPLIER", options=[""] + SUPPLIER_OPTIONS)
            inspected_by = st.selectbox("INSPECTED BY", options=[""] + INSPECTED_BY_OPTIONS)
            date_first_used = st.date_input("DATE OF FIRST USED", value=None)
            date_last_used = st.date_input("DATE OF LAST USED", value=None)
            
        col_insp1, col_insp2 = st.columns(2)
        with col_insp1:
            inspection_date = st.date_input("INSPECTION DATE", value=date.today())
        with col_insp2:
            next_inspection_date = st.date_input("NEXT INSPECTION DATE", value=date.today())
            
        comment = st.text_area("COMMENT")
        submit_btn = st.form_submit_button("Save Equipment Record", type="primary")
        
        if submit_btn:
            if not item_code:
                st.error("Submission failed: ITEM CODE is a required field.")
            else:
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('''
                    INSERT INTO register (
                        item_code, manufacture, product, date_of_purchase, equipment_name, standard, 
                        year_of_manufacture, doc_del, supplier, date_of_first_used, 
                        date_of_last_used, inspection_date, next_inspection_date, 
                        inspected_by, comment
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    item_code, manufacture, product, str(date_of_purchase) if date_of_purchase else "", equipment_name, standard, 
                    int(year_of_manufacture), doc_del, supplier, str(date_first_used) if date_first_used else "", str(date_last_used) if date_last_used else "",
                    str(inspection_date) if inspection_date else "", str(next_inspection_date) if next_inspection_date else "", inspected_by, comment
                ))
                conn.commit()
                conn.close()
                st.success(f"Successfully added Item Code: {item_code}")
                st.rerun()

# ==========================================
# TAB 1: VIEW, FILTER & EDIT RECORDS
# ==========================================
with tab_view:
    df = load_data()
    
    if df.empty:
        st.info("The database register is currently empty. Add records to begin tracking.")
    else:
        df['db_backend_id'] = df['sn']
        df['sn'] = range(1, len(df) + 1)
        
        df_display = df.rename(columns={
            "sn": "S.N", "item_code": "ITEM CODE", "manufacture": "MANUFACTURE",
            "product": "PRODUCT", "date_of_purchase": "DATE OF PURCHASE",
            "equipment_name": "EQUIPMENT NAME", "standard": "STANDARD",
            "year_of_manufacture": "YEAR OF MANUFACTURE", "doc_del": "DOC/DEL",
            "supplier": "SUPPLIER", "date_of_first_used": "DATE OF FIRST USED",
            "date_of_last_used": "DATE OF LAST USED", "inspection_date": "INSPECTION DATE",
            "next_inspection_date": "NEXT INSPECTION DATE", "inspected_by": "INSPECTED BY", "comment": "COMMENT"
        })
        
        columns_order = [
            "S.N", "ITEM CODE", "MANUFACTURE", "PRODUCT", "DATE OF PURCHASE", "EQUIPMENT NAME", "STANDARD", 
            "YEAR OF MANUFACTURE", "DOC/DEL", "SUPPLIER", "DATE OF FIRST USED", 
            "DATE OF LAST USED", "INSPECTION DATE", "NEXT INSPECTION DATE", "INSPECTED BY", "COMMENT", "db_backend_id"
        ]
        df_display = df_display[columns_order]
        
        st.subheader("🔍 Filter & Export Registry Entries")
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            search_query = st.text_input("Global Search (Item Code / Product / Equipment Name / Standard)", "")
        with f_col2:
            m_filter = st.multiselect("Filter by Manufacture", options=MANUFACTURE_OPTIONS)
        with f_col3:
            s_filter = st.multiselect("Filter by Supplier", options=SUPPLIER_OPTIONS)
            
        if search_query:
            df_display = df_display[
                df_display["ITEM CODE"].str.contains(search_query, case=False, na=False) |
                df_display["PRODUCT"].str.contains(search_query, case=False, na=False) |
                df_display["EQUIPMENT NAME"].str.contains(search_query, case=False, na=False) |
                df_display["STANDARD"].str.contains(search_query, case=False, na=False)
            ]
        if m_filter:
            df_display = df_display[df_display["MANUFACTURE"].isin(m_filter)]
        if s_filter:
            df_display = df_display[df_display["SUPPLIER"].isin(s_filter)]
            
        if not df_display.empty:
            df_display["S.N"] = range(1, len(df_display) + 1)

        st.markdown("### 📊 Live Stock Metrics")
        count_col1, count_col2 = st.columns(2)
        with count_col1:
            with st.expander("📝 Counts by PRODUCT Category", expanded=True):
                prod_counts = df_display["PRODUCT"].replace("", "Unspecified").value_counts().reset_index()
                prod_counts.columns = ["PRODUCT TYPE", "TOTAL QTY"]
                st.dataframe(prod_counts, use_container_width=True, hide_index=True)
        with count_col2:
            with st.expander("⚙️ Counts by EQUIPMENT NAME Reference", expanded=True):
                equip_counts = df_display["EQUIPMENT NAME"].replace("", "Unspecified").value_counts().reset_index()
                equip_counts.columns = ["EQUIPMENT MODEL NAME", "TOTAL QTY"]
                st.dataframe(equip_counts, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.write("### Current Active Register View")
        
        st.dataframe(
            df_display.drop(columns=["db_backend_id"]),
            use_container_width=True,
            hide_index=True,
            column_config={
                "S.N": st.column_config.NumberColumn(format="%d"),
                "YEAR OF MANUFACTURE": st.column_config.NumberColumn(format="%d")
            }
        )
        
        csv_data = df_display.drop(columns=["db_backend_id"]).to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Current View to CSV Ledger",
            data=csv_data,
            file_name=f"equipment_register_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
        st.markdown("---")
        st.subheader("🛠️ Record Management Panel")
        visual_sn_list = df_display["S.N"].tolist()
        selected_visual_sn = st.selectbox("Select S.N to Edit or Delete from the view grid above", options=[""] + visual_sn_list)
        
        if selected_visual_sn != "":
            row_data = df_display[df_display["S.N"] == selected_visual_sn].iloc[0]
            actual_db_id = int(row_data["db_backend_id"])
            
            sub_edit_tab, sub_del_tab = st.tabs(["📝 Edit Record Data", "🗑️ Delete Record Entry"])
            
            with sub_edit_tab:
                with st.form(key=f"edit_form_{actual_db_id}"):
                    e_col1, e_col2, e_col3 = st.columns(3)
                    with e_col1:
                        edit_item_code = st.text_input("ITEM CODE*", value=str(row_data["ITEM CODE"]))
                        m_val = row_data["MANUFACTURE"]
                        m_idx = MANUFACTURE_OPTIONS.index(m_val) + 1 if m_val in MANUFACTURE_OPTIONS else 0
                        edit_manufacture = st.selectbox("MANUFACTURE", options=[""] + MANUFACTURE_OPTIONS, index=m_idx)
                        edit_product = st.text_input("PRODUCT", value=str(row_data["PRODUCT"] or ""))
                        edit_purchase_date = st.date_input("DATE OF PURCHASE", value=parse_db_date(row_data["DATE OF PURCHASE"]))
                    with e_col2:
                        edit_equipment_name = st.text_input("EQUIPMENT NAME", value=str(row_data["EQUIPMENT NAME"] or ""))
                        edit_standard = st.text_input("STANDARD", value=str(row_data["STANDARD"] or ""))
                        edit_year = st.number_input("YEAR OF MANUFACTURE", min_value=1990, max_value=datetime.now().year + 5, value=int(row_data["YEAR OF MANUFACTURE"] or datetime.now().year))
                        edit_doc_del = st.text_input("DOC/DEL", value=str(row_data["DOC/DEL"] or ""))
                    with e_col3:
                        s_val = row_data["SUPPLIER"]
                        s_idx = SUPPLIER_OPTIONS.index(s_val) + 1 if s_val in SUPPLIER_OPTIONS else 0
                        edit_supplier = st.selectbox("SUPPLIER", options=[""] + SUPPLIER_OPTIONS, index=s_idx)
                        i_val = row_data["INSPECTED BY"]
                        i_idx = INSPECTED_BY_OPTIONS.index(i_val) + 1 if i_val in INSPECTED_BY_OPTIONS else 0
                        edit_inspected_by = st.selectbox("INSPECTED BY", options=[""] + INSPECTED_BY_OPTIONS, index=i_idx)
                        edit_first_used = st.date_input("DATE OF FIRST USED", value=parse_db_date(row_data["DATE OF FIRST USED"]))
                        edit_last_used = st.date_input("DATE OF LAST USED", value=parse_db_date(row_data["DATE OF LAST USED"]))
                    
                    e_insp1, e_insp2 = st.columns(2)
                    with e_insp1:
                        edit_inspection_date = st.date_input("INSPECTION DATE", value=parse_db_date(row_data["INSPECTION DATE"]) or date.today())
                    with e_insp2:
                        edit_next_inspection_date = st.date_input("NEXT INSPECTION DATE", value=parse_db_date(row_data["NEXT INSPECTION DATE"]) or date.today())
                        
                    edit_comment = st.text_area("COMMENT", value=str(row_data["COMMENT"] or ""))
                    update_btn = st.form_submit_button("Apply Changes", type="primary")
                    
                    if update_btn:
                        if not edit_item_code:
                            st.error("Modification failed: ITEM CODE cannot be empty.")
                        else:
                            conn = sqlite3.connect(DB_FILE)
                            c = conn.cursor()
                            c.execute('''
                                UPDATE register 
                                SET item_code = ?, manufacture = ?, product = ?, date_of_purchase = ?, equipment_name = ?, 
                                    standard = ?, year_of_manufacture = ?, doc_del = ?, 
                                    supplier = ?, date_of_first_used = ?, date_of_last_used = ?, 
                                    inspection_date = ?, next_inspection_date = ?, 
                                    inspected_by = ?, comment = ?
                                WHERE sn = ?
                            ''', (
                                edit_item_code, edit_manufacture, edit_product, str(edit_purchase_date) if edit_purchase_date else "", edit_equipment_name,
                                edit_standard, int(edit_year), edit_doc_del, edit_supplier, 
                                str(edit_first_used) if edit_first_used else "", str(edit_last_used) if edit_last_used else "", 
                                str(edit_inspection_date) if edit_inspection_date else "", str(edit_next_inspection_date) if edit_next_inspection_date else "",
                                edit_inspected_by, edit_comment, actual_db_id
                            ))
                            conn.commit()
                            conn.close()
                            st.success("Record updated successfully.")
                            st.rerun()
                            
            with sub_del_tab:
                st.warning(f"Warning: Deleting record S.N {selected_visual_sn}.")
                if st.button("Confirm Permanent Deletion", type="primary", key=f"del_{actual_db_id}"):
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("DELETE FROM register WHERE sn = ?", (actual_db_id,))
                    conn.commit()
                    conn.close()
                    st.success("Record deleted successfully.")
                    st.rerun()