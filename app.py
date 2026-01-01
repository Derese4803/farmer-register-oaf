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

engine = create_engine("sqlite:///./survey_secure.db", connect_args={"check_same_thread": False})
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

def nav(p):
    st.session_state["page"] = p
    st.rerun()

# --- 4. PAGE: HOME ---
if st.session_state["page"] == "Home":
    st.title("🌾 Amhara Survey 2025")
    if st.session_state["editor"]:
        st.success(f"👤 Current Editor: **{st.session_state['editor']}**")
    
    st.divider()
    col1, col2 = st.columns(2)
    if col1.button("📝 NEW REGISTRATION", use_container_width=True, type="primary"): nav("Reg")
    if col2.button("📊 ADMIN DASHBOARD", use_container_width=True): nav("Data")

# --- 5. PAGE: REGISTRATION ---
elif st.session_state["page"] == "Reg":
    st.button("⬅️ Back", on_click=lambda: nav("Home"))
    
    if not st.session_state["editor"]:
        with st.container(border=True):
            st.subheader("Editor Identification")
            name_in = st.text_input("Registered By (Enter Name):")
            if st.button("Start Working"):
                if name_in.strip():
                    st.session_state["editor"] = name_in.strip()
                    st.rerun()
    else:
        with st.form("reg_form", clear_on_submit=True):
            st.info(f"Editor: {st.session_state['editor']}")
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
                    st.success("✅ Saved Successfully!")

# --- 6. PAGE: ADMIN (PASSCODE PROTECTED) ---
elif st.session_state["page"] == "Data":
    st.button("⬅️ Back", on_click=lambda: nav("Home"))
    
    # --- PASSCODE LOCK ---
    if not st.session_state["auth"]:
        st.header("🔒 Admin Access Required")
        pass_input = st.text_input("Enter Admin Passcode", type="password")
        if st.button("Unlock Dashboard"):
            if pass_input == "oaf2025": 
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("❌ Incorrect Passcode")
    
    # --- PROTECTED CONTENT ---
    else:
        db = SessionLocal()
        farmers = db.query(Farmer).order_by(Farmer.id.desc()).all()
        
        col_title, col_logout = st.columns([8, 2])
        col_title.header("📊 Secure Admin Dashboard")
        if col_logout.button("🔒 Logout Admin"):
            st.session_state["auth"] = False
            st.rerun()

        if farmers:
            # DOWNLOADS
            c1, c2 = st.columns(2)
            df = pd.DataFrame([{"ID": f.id, "Name": f.name, "Woreda": f.woreda, "Editor": f.registered_by, "Date": f.timestamp} for f in farmers])
            c1.download_button("📥 Excel Download", df.to_csv(index=False).encode('utf-8-sig'), "SurveyData.csv", use_container_width=True)
            
            z_buf = BytesIO()
            with zipfile.ZipFile(z_buf, "w") as zf:
                for f in farmers:
                    if f.audio_data: zf.writestr(f"ID_{f.id}_{f.name}.mp3", base64.b64decode(f.audio_data))
            c2.download_button("🎤 Audio ZIP", z_buf.getvalue(), "Audios.zip", use_container_width=True)

            st.divider()

            # GLOBAL DELETE
            st.error("🚨 DANGER ZONE")
            if st.button("🗑️ DELETE ALL RECORDS PERMANENTLY", type="primary", use_container_width=True):
                db.query(Farmer).delete()
                db.commit()
                st.rerun()

            st.divider()

            # VIEW LIST (READ ONLY)
            st.subheader("📝 Registered Farmers")
            for f in farmers:
                st.text(f"ID: {f.id} | {f.name} ({f.woreda}) | Registered By: {f.registered_by}")
        else:
            st.info("Database is currently empty.")
        db.close()
