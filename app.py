import streamlit as st
import pandas as pd
import base64
import zipfile
import datetime
from io import BytesIO
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base

# --- 1. DATABASE SETUP ---
Base = declarative_base()

class Farmer(Base):
    __tablename__ = 'farmers'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    name = Column(String, nullable=False)
    woreda = Column(String)
    phone = Column(String)
    audio_data = Column(Text) 
    registered_by = Column(String)

engine = create_engine("sqlite:///./survey_2025.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

# --- 2. HELPERS ---
def to_b64(file):
    if file: return base64.b64encode(file.getvalue()).decode()
    return None

# --- 3. SESSION STATE ---
if "page" not in st.session_state: st.session_state["page"] = "Home"
if "auth" not in st.session_state: st.session_state["auth"] = False
if "editor" not in st.session_state: st.session_state["editor"] = None
if "edit_id" not in st.session_state: st.session_state["edit_id"] = None

def nav(p):
    st.session_state["page"] = p
    st.rerun()

# --- 4. PAGE: HOME ---
if st.session_state["page"] == "Home":
    st.title("🌾 Amhara Survey 2025")
    if st.session_state["editor"]:
        st.success(f"👤 Editor: **{st.session_state['editor']}**")
    
    st.divider()
    col1, col2 = st.columns(2)
    if col1.button("📝 NEW REGISTRATION", use_container_width=True, type="primary"): nav("Reg")
    if col2.button("📊 VIEW & MANAGE DATA", use_container_width=True): nav("Data")

# --- 5. PAGE: REGISTRATION ---
elif st.session_state["page"] == "Reg":
    st.button("⬅️ Home", on_click=lambda: nav("Home"))
    
    if not st.session_state["editor"]:
        with st.container(border=True):
            st.subheader("Editor Login (Enter Name Once)")
            name_in = st.text_input("Registered By:")
            if st.button("Start"):
                if name_in.strip():
                    st.session_state["editor"] = name_in.strip()
                    st.rerun()
    else:
        with st.form("reg_form", clear_on_submit=True):
            st.info(f"Active Editor: {st.session_state['editor']}")
            f_name = st.text_input("Farmer Name")
            woreda = st.text_input("Woreda")
            phone = st.text_input("Phone Number")
            audio = st.file_uploader("🎤 Audio Recording", type=['mp3','wav','m4a'])
            
            if st.form_submit_button("Save Registration"):
                if f_name and woreda:
                    db = SessionLocal()
                    db.add(Farmer(name=f_name, woreda=woreda, phone=phone, 
                                  audio_data=to_b64(audio), registered_by=st.session_state["editor"]))
                    db.commit(); db.close()
                    st.success("✅ Saved!")
                else:
                    st.error("Name and Woreda are required.")

# --- 6. PAGE: DATA MANAGEMENT (Individual Records & Downloads) ---
elif st.session_state["page"] == "Data":
    st.button("⬅️ Home", on_click=lambda: nav("Home"))
    
    if not st.session_state["auth"]:
        pwd = st.text_input("Admin Passcode", type="password")
        if pwd == "oaf2025": 
            st.session_state["auth"] = True
            st.rerun()
    else:
        db = SessionLocal()
        farmers = db.query(Farmer).order_by(Farmer.id.desc()).all()
        
        st.header("📊 Management & Downloads")

        if farmers:
            # --- TOP SECTION: DOWNLOADS & DELETE ALL ---
            col_dl1, col_dl2, col_del = st.columns([1,1,1])
            
            # Excel Download
            df = pd.DataFrame([{
                "ID": f.id, "Name": f.name, "Woreda": f.woreda, "Phone": f.phone,
                "Editor": f.registered_by, "Date": f.timestamp
            } for f in farmers])
            col_dl1.download_button("📥 Excel (CSV)", df.to_csv(index=False).encode('utf-8-sig'), "SurveyData.csv", "text/csv")
            
            # Audio ZIP Download
            z_buf = BytesIO()
            with zipfile.ZipFile(z_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in farmers:
                    if f.audio_data:
                        zf.writestr(f"ID_{f.id}_{f.name}.mp3", base64.b64decode(f.audio_data))
            col_dl2.download_button("🎤 Audio ZIP", z_buf.getvalue(), "Audios.zip", "application/zip")
            
            # GLOBAL DELETE ALL BUTTON
            if col_del.button("🗑️ DELETE ALL RECORDS", type="primary", use_container_width=True):
                db.query(Farmer).delete()
                db.commit()
                st.rerun()

            st.divider()
        else:
            st.info("No records found.")
        db.close()
