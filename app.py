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

engine = create_engine("sqlite:///./survey_final.db", connect_args={"check_same_thread": False})
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
    st.title("🌾 Amhara M&E survey 2026")
    if st.session_state["editor"]:
        st.success(f"👤 Active Editor: **{st.session_state['editor']}**")
    
    st.divider()
    col1, col2 = st.columns(2)
    if col1.button("📝 NEW REGISTRATION", use_container_width=True, type="primary"): nav("Reg")
    if col2.button("📊 VIEW & DELETE DATA", use_container_width=True): nav("Data")

# --- 5. PAGE: REGISTRATION ---
elif st.session_state["page"] == "Reg":
    st.button("⬅️ Home", on_click=lambda: nav("Home"))
    
    if not st.session_state["editor"]:
        with st.container(border=True):
            st.subheader("Login Once")
            name_in = st.text_input("Enter Your Name (Registered By):")
            if st.button("Login"):
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
            
            if st.form_submit_button("Save"):
                if f_name and woreda:
                    db = SessionLocal()
                    db.add(Farmer(name=f_name, woreda=woreda, phone=phone, 
                                  audio_data=to_b64(audio), registered_by=st.session_state["editor"]))
                    db.commit(); db.close()
                    st.success("✅ Saved!")

# --- 6. PAGE: DATA MANAGEMENT (ONLY DELETE ALL) ---
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
        
        st.header("📊 Admin Dashboard")

        if farmers:
            # --- GLOBAL ACTIONS (Downloads) ---
            c1, c2 = st.columns(2)
            
            # Excel Download
            df = pd.DataFrame([{
                "ID": f.id, "Name": f.name, "Woreda": f.woreda, "Phone": f.phone,
                "Editor": f.registered_by, "Date": f.timestamp
            } for f in farmers])
            c1.download_button("📥 Download Excel", df.to_csv(index=False).encode('utf-8-sig'), "Data.csv", use_container_width=True)
            
            # Audio ZIP Download
            z_buf = BytesIO()
            with zipfile.ZipFile(z_buf, "w") as zf:
                for f in farmers:
                    if f.audio_data: 
                        zf.writestr(f"ID_{f.id}_{f.name}.mp3", base64.b64decode(f.audio_data))
            c2.download_button("🎤 Download Audios (ZIP)", z_buf.getvalue(), "Audios.zip", use_container_width=True)

            st.divider()

            # --- THE ONLY DELETE ACTION: DELETE ALL ---
            st.warning("⚠️ Warning: The button below will permanently erase all data.")
            if st.button("🗑️ DELETE ALL RECORDS FROM DATABASE", type="primary", use_container_width=True):
                db.query(Farmer).delete()
                db.commit()
                st.success("All records have been deleted.")
                st.rerun()

            st.divider()

            # --- DISPLAY LIST ONLY (NO BUTTONS) ---
            st.subheader("📝 Current Records List")
            for f in farmers:
                st.write(f"**ID: {f.id}** | {f.name} ({f.woreda}) | 👤 Registered By: {f.registered_by}")
        else:
            st.info("Database is empty.")
        db.close()
