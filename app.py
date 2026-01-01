import streamlit as st
import pandas as pd
import base64
import zipfile
from io import BytesIO
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from database import SessionLocal, engine
from models import Farmer, Woreda, Kebele, create_tables

# --- SETUP ---
st.set_page_config(page_title="2025 Amhara Survey", page_icon="🌾", layout="wide")
create_tables()

if "current_page" not in st.session_state: st.session_state["current_page"] = "Home"
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False

def nav(page):
    st.session_state["current_page"] = page
    st.rerun()

# --- HELPER FUNCTIONS ---
def to_base64(uploaded_file):
    if uploaded_file:
        return base64.b64encode(uploaded_file.getvalue()).decode()
    return None

@st.cache_resource
def init_gsheet():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json(creds_dict, scope)
        return gspread.authorize(creds).open('2025 Amhara Planting Survey').get_worksheet(0)
    except: return None

# --- PAGES ---
def home_page():
    st.title("🌾 Amhara Planting Survey 2025")
    st.write(f"User: **{st.session_state['username']}**")
    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("📝 NEW REGISTRATION", use_container_width=True, type="primary"): nav("Register")
    if c1.button("📍 SETUP LOCATIONS", use_container_width=True): nav("Locations")
    if c2.button("💾 EXPORT DATA", use_container_width=True): nav("Download")
    if c2.button("🛠️ EDIT RECORDS", use_container_width=True): nav("Edit")

def register_page():
    st.button("⬅️ Back", on_click=lambda: nav("Home"))
    st.header("📝 Farmer Registration")
    db = SessionLocal()
    woredas = db.query(Woreda).all()
    
    with st.form("reg_form", clear_on_submit=True):
        name = st.text_input("Farmer Full Name")
        sel_woreda = st.selectbox("Select Woreda", ["Select..."] + [w.name for w in woredas])
        
        kebeles = []
        if sel_woreda != "Select...":
            w_obj = db.query(Woreda).filter(Woreda.name == sel_woreda).first()
            kebeles = [k.name for k in w_obj.kebeles] if w_obj else []
        
        sel_kebele = st.selectbox("Select Kebele", ["Select..."] + kebeles)
        phone = st.text_input("Phone Number")
        audio = st.file_uploader("🎤 Upload Audio", type=['mp3', 'wav', 'm4a'])
        
        if st.form_submit_button("Save Registration"):
            if name and sel_woreda != "Select..." and sel_kebele != "Select...":
                new_farmer = Farmer(
                    name=name, woreda=sel_woreda, kebele=sel_kebele,
                    phone=phone, audio_data=to_base64(audio),
                    registered_by=st.session_state["username"]
                )
                db.add(new_farmer); db.commit()
                st.success("✅ Saved!")
            else: st.error("Missing Info")
    db.close()

def download_page():
    st.button("⬅️ Back", on_click=lambda: nav("Home"))
    db = SessionLocal()
    farmers = db.query(Farmer).all()
    if farmers:
        df = pd.DataFrame([{"ID": f.id, "Farmer": f.name, "Woreda": f.woreda, "Kebele": f.kebele, "Phone": f.phone} for f in farmers])
        st.dataframe(df, use_container_width=True)
        
        # Audio ZIP
        buf = BytesIO()
        with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED) as zf:
            for f in farmers:
                if f.audio_data:
                    zf.writestr(f"{f.name}_{f.kebele}.mp3", base64.b64decode(f.audio_data))
        
        st.download_button("📥 Download Excel", df.to_csv(index=False).encode('utf-8-sig'), "Survey_Data.csv")
        st.download_button("🎤 Download Audios (ZIP)", buf.getvalue(), "Audios.zip")
    db.close()

def manage_locations():
    st.button("⬅️ Back", on_click=lambda: nav("Home"))
    db = SessionLocal()
    if st.button("🔄 Sync Woredas from Google Sheets"):
        sheet = init_gsheet()
        if sheet:
            records = sheet.get_all_records()
            for r in records:
                w_name = str(r.get("Woreda", "")).strip()
                if w_name and not db.query(Woreda).filter(Woreda.name == w_name).first():
                    db.add(Woreda(name=w_name))
            db.commit(); st.success("Synced!")
    
    st.divider()
    uploaded = st.file_uploader("Bulk Upload Locations (CSV: Woreda, Kebele)", type="csv")
    if uploaded:
        df = pd.read_csv(uploaded)
        for _, r in df.iterrows():
            w_n, k_n = str(r['Woreda']).strip(), str(r['Kebele']).strip()
            w_obj = db.query(Woreda).filter(Woreda.name == w_n).first()
            if not w_obj:
                w_obj = Woreda(name=w_n); db.add(w_obj); db.commit()
            if not db.query(Kebele).filter(Kebele.name == k_n, Kebele.woreda_id == w_obj.id).first():
                db.add(Kebele(name=k_n, woreda_id=w_obj.id))
        db.commit(); st.success("Uploaded!")
    db.close()

# --- MAIN ---
def main():
    if not st.session_state["logged_in"]:
        st.title("🚜 Survey Login")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            if u == "admin" and p == "oaf2025": # Simple auth
                st.session_state["logged_in"] = True
                st.session_state["username"] = u
                st.rerun()
            else: st.error("Invalid")
    else:
        pg = st.session_state["current_page"]
        if pg == "Home": home_page()
        elif pg == "Register": register_page()
        elif pg == "Locations": manage_locations()
        elif pg == "Download": download_page()

if __name__ == "__main__": main()
