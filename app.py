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

# Initialize Navigation State
if "current_page" not in st.session_state: 
    st.session_state["current_page"] = "Home"

# Function to handle navigation
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
    except: 
        return None

# --- PAGES ---
def home_page():
    st.title("🌾 Amhara Planting Survey 2025")
    st.write("Survey Management Dashboard")
    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📝 NEW REGISTRATION", use_container_width=True, type="primary"): 
            nav("Register")
        if st.button("📍 SETUP LOCATIONS", use_container_width=True): 
            nav("Locations")
    with c2:
        if st.button("💾 EXPORT DATA", use_container_width=True): 
            nav("Download")
        if st.button("🛠️ EDIT RECORDS", use_container_width=True): 
            nav("Edit")

def register_page():
    st.button("⬅️ Back to Home", on_click=lambda: nav("Home"))
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
        audio = st.file_uploader("🎤 Upload Audio Recording", type=['mp3', 'wav', 'm4a'])
        
        if st.form_submit_button("Save Registration"):
            if name and sel_woreda != "Select..." and sel_kebele != "Select...":
                new_farmer = Farmer(
                    name=name, 
                    woreda=sel_woreda, 
                    kebele=sel_kebele,
                    phone=phone, 
                    audio_data=to_base64(audio),
                    registered_by="Open Access" # No specific user logged in
                )
                db.add(new_farmer); db.commit()
                st.success(f"✅ Record for {name} saved successfully!")
            else: 
                st.error("⚠️ Please provide Name, Woreda, and Kebele.")
    db.close()

def download_page():
    st.button("⬅️ Back to Home", on_click=lambda: nav("Home"))
    st.header("📊 Export Data")
    db = SessionLocal()
    farmers = db.query(Farmer).all()
    if farmers:
        df = pd.DataFrame([{
            "ID": f.id, 
            "Farmer": f.name, 
            "Woreda": f.woreda, 
            "Kebele": f.kebele, 
            "Phone": f.phone,
            "Date": f.timestamp
        } for f in farmers])
        st.dataframe(df, use_container_width=True)
        
        # Audio ZIP logic
        buf = BytesIO()
        with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED) as zf:
            for f in farmers:
                if f.audio_data:
                    zf.writestr(f"Audio_{f.id}_{f.name}.mp3", base64.b64decode(f.audio_data))
        
        c1, c2 = st.columns(2)
        c1.download_button("📥 Download Excel (CSV)", df.to_csv(index=False).encode('utf-8-sig'), "Survey_Data.csv", use_container_width=True)
        c2.download_button("🎤 Download All Audios (ZIP)", buf.getvalue(), "Audios.zip", use_container_width=True)
    else:
        st.info("No
