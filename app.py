import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- EXTERNAL FILE IMPORTS ---
try:
    from database import SessionLocal
    from models import Farmer, Woreda, Kebele, create_tables
    from auth import login_user
except ImportError:
    st.error("⚠️ System Files Missing! Please ensure models.py, database.py, and auth.py are in your repository.")
    st.stop()

# --- INITIAL SETUP ---
st.set_page_config(page_title="2025 Amhara Planting Survey", page_icon="🌾", layout="wide")
AUDIO_UPLOAD_DIR = "uploads"
os.makedirs(AUDIO_UPLOAD_DIR, exist_ok=True)
create_tables()

# Initialize Navigation State
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Home"

def change_page(page_name):
    st.session_state["current_page"] = page_name
    st.rerun()

# --- GOOGLE SHEETS CONNECTION ---
@st.cache_resource
def initialize_gsheets():
    try:
        service_account_info = st.secrets["gcp_service_account"]
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json(service_account_info, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open('2025 Amhara Planting Survey') 
        return spreadsheet.get_worksheet(0)
    except Exception as e:
        return None

# --- PAGE: HOME (DASHBOARD) ---
def home_page():
    st.title(f"🌾 2025 Amhara Planting Survey")
    st.info(f"Welcome back, **{st.session_state['username']}**")
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 NEW REGISTRATION", use_container_width=True, type="primary"):
            change_page("Registration")
        if st.button("📍 SETUP LOCATIONS (Woreda/Kebele)", use_container_width=True):
            change_page("Locations")
    with col2:
        if st.button("💾 EXPORT & DOWNLOAD DATA", use_container_width=True):
            change_page("Download")
        if st.button("🛠️ EDIT/DELETE RECORDS", use_container_width=True):
            change_page("EditRecords")

# --- PAGE: REGISTRATION ---
def register_page():
    if st.button("⬅️ Back to Home"): change_page("Home")
    st.header("📝 Farmer Registration Form")
    db = SessionLocal()
    
    # Fetch Woredas for dropdown
    woreda_objs = db.query(Woreda).all()
    woreda_names = [w.name for w in woreda_objs]

    with st.form("reg_form", clear_on_submit=True):
        name = st.text_input("Farmer Full Name")
        
        # Select Woreda
        sel_woreda = st.selectbox("Select Woreda", ["Select..."] + woreda_names)
        
        # Dynamic Kebele Selection
        kebeles = []
        if sel_woreda != "Select...":
            w_obj = db.query(Woreda).filter(Woreda.name == sel_woreda).first()
            if w_obj:
                kebeles = [k.name for k in w_obj.kebeles]
        
        sel_kebele = st.selectbox("Select Kebele", ["Select..."] + kebeles if kebeles else ["No Kebeles Found"])
        phone = st.text_input("Phone Number")
        audio_file = st.file_uploader("🎤 Upload Audio Recording", type=["mp3", "wav", "m4a"])
        
        if st.form_submit_button("Save Registration"):
            if not name or sel_woreda == "Select..." or sel_kebele == "Select...":
                st.error("⚠️ Please fill Name, Woreda, and Kebele.")
            else:
                path = None
                if audio_file:
                    path = os.path.join(AUDIO_UPLOAD_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{audio_file.name}")
                    with open(path, "wb") as f: f.write(audio_file.getbuffer())
                
                new_entry = Farmer(
                    name=name, woreda=sel_woreda, kebele=sel_kebele,
                    phone=phone, audio_path=path,
                    registered_by=st.session_state["username"]
                )
                db.add(new_entry)
                db.commit()
                st.success(f"✅ Record for {name} saved!")
    db.close()

# --- PAGE: SETUP LOCATIONS ---
def manage_locations():
    if st.button("⬅️ Back to Home"): change_page("Home")
    st.header("📍 Manage Woredas & Kebeles")
    db = SessionLocal()
    
    t1, t2 = st.tabs(["📥 Import & Sync", "✏️ Edit/Delete List"])
    
    with t1:
        st.subheader("🔗 Google Sheet Sync")
        if st.button("🔄 Pull Woredas from GSheet"):
            sheet = initialize_gsheets()
            if sheet:
                records = sheet.get_all_records()
                count = 0
                for r in records:
                    w_name = str(r.get("Woreda", r.get("Dep", ""))).strip()
                    if w_name and not db.query(Woreda).filter(Woreda.name == w_name).first():
                        db.add(Woreda(name=w_name))
                        count += 1
                db.commit()
                st.success(f"✅ {count} New Woredas Imported!")
            else: st.error("Sync Failed! Check GSheet Name or Secrets.")
        
        st.divider()
        st.subheader("📄 Excel/CSV Bulk Upload")
        uploaded = st.file_uploader("Upload CSV (Columns: Woreda, Kebele)", type="csv")
        if uploaded:
            df = pd.read_csv(uploaded)
            for _, r in df.iterrows():
                w_n, k_n = str(r['Woreda']).strip(), str(r['Kebele']).strip()
                w_obj = db.query(Woreda).filter(Woreda.name == w_n).first()
                if not w_obj:
                    w_obj = Woreda(name=w_n); db.add(w_obj); db.commit()
                if not db.query(Kebele).filter(Kebele.name == k_n, Kebele.woreda_id == w_obj.id).first():
                    db.add(Kebele(name=k_n, woreda_id=w_obj.id))
            db.commit(); st.success("✅ Locations Uploaded!")

    with t2:
        woredas = db.query(Woreda).all()
        for w in woredas:
            with st.expander(f"📌 {w.name}"):
                c1, c2, c3 = st.columns([2, 1, 1])
                new_w = c1.text_input("Rename Woreda", w.name, key=f"w{w.id}")
                if c2.button("Update", key=f"ub{w.id}"):
                    w.name = new_w; db.commit(); st.rerun()
                if c3.button("🗑️ Delete Woreda", key=f"dw{w.id}"):
                    db.delete(w); db.commit(); st.rerun()
                
                for k in w.kebeles:
                    ck1, ck2 = st.columns([3, 1])
                    ck1.write(f"• {k.name}")
                    if ck2.button("🗑️", key=f"dk{k.id}"):
                        db.delete(k); db.commit(); st.rerun()
    db.close()

# --- PAGE: EDIT RECORDS ---
def edit_records_page():
    if st.button("⬅️ Back to Home"): change_page("Home")
    st.header("🛠️ Edit Farmer Data")
    db = SessionLocal()
    farmers = db.query(Farmer).all()
    for f in farmers:
        with st.expander(f"👤 {f.name} - {f.kebele}"):
            c1, c2 = st.columns(2)
            n_name = c1.text_input("Edit Name", f.name, key=f"fn{f.id}")
            n_phone = c2.text_input("Edit Phone", f.phone, key=f"fp{f.id}")
            if st.button("Save Changes", key=f"fs{f.id}"):
                f.name, f.phone = n_name, n_phone
                db.commit(); st.success("Updated!"); st.rerun()
            if st.button("🗑️ Delete Record", key=f"fdel{f.id}", type="secondary"):
                db.delete(f); db.commit(); st.rerun()
    db.close()

# --- PAGE: DOWNLOAD ---
def download_page():
    if st.button("⬅️ Back to Home"): change_page("Home")
    st.header("💾 Export Survey Data")
    db = SessionLocal()
    farmers = db.query(Farmer).all()
    if farmers:
        df = pd.DataFrame([{
            "Farmer": f.name, "Woreda": f.woreda, "Kebele": f.kebele, 
            "Phone": f.phone, "Surveyor": f.registered_by, "Date": f.timestamp
        } for f in farmers])
        st.dataframe(df, use_container_width=True)
        # Use utf-8-sig so Excel handles Ethiopian names correctly
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Download Excel (CSV)", csv, "Amhara_Survey_Data.csv", "text/csv")
    else: st.info("No records found.")
    db.close()

# --- MAIN NAVIGATION ---
def main():
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        st.title("🚜 2025 Amhara Survey Login")
        with st.container(border=True):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Enter System", use_container_width=True, type="primary"):
                if login_user(u, p):
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = u
                    st.rerun()
                else: st.error("❌ Invalid Username or Password")
    else:
        st.sidebar.write(f"Logged in as: **{st.session_state['username']}**")
        if st.sidebar.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
            
        page = st.session_state["current_page"]
        if page == "Home": home_page()
        elif page == "Registration": register_page()
        elif page == "Locations": manage_locations()
        elif page == "Download": download_page()
        elif page == "EditRecords": edit_records_page()

if __name__ == "__main__":
    main()
