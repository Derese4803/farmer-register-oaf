import streamlit as st
import pandas as pd
import base64
import zipfile
import datetime
from io import BytesIO, StringIO
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
    kebele = Column(String)
    phone = Column(String)
    audio_data = Column(Text) 
    registered_by = Column(String)

engine = create_engine("sqlite:///./survey_final.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

# --- 2. HELPERS ---
def to_b64(file):
    if file:
        return base64.b64encode(file.getvalue()).decode()
    return None

# --- 3. APP CONFIG ---
st.set_page_config(page_title="Amhara 2025", layout="wide")

if "page" not in st.session_state: st.session_state["page"] = "Home"
if "auth" not in st.session_state: st.session_state["auth"] = False
if "editor" not in st.session_state: st.session_state["editor"] = None
if "edit_id" not in st.session_state: st.session_state["edit_id"] = None

def nav(p):
    st.session_state["page"] = p
    st.rerun()

# --- 4. PAGE: HOME ---
if st.session_state["page"] == "Home":
    st.title("🌾 Amhara Planting Survey 2025")
    if st.session_state["editor"]:
        st.success(f"👤 Active Editor: **{st.session_state['editor']}**")
    
    st.divider()
    col1, col2 = st.columns(2)
    if col1.button("📝 NEW REGISTRATION", use_container_width=True, type="primary"): nav("Reg")
    if col2.button("📊 ADMIN DASHBOARD", use_container_width=True): nav("Data")

# --- 5. PAGE: REGISTRATION ---
elif st.session_state["page"] == "Reg":
    st.button("⬅️ Home", on_click=lambda: nav("Home"))
    
    if not st.session_state["editor"]:
        st.subheader("Login Once")
        name_in = st.text_input("Editor Name:")
        if st.button("Start"):
            if name_in: 
                st.session_state["editor"] = name_in
                st.rerun()
    else:
        with st.form("main_form", clear_on_submit=True):
            st.write(f"Editor: {st.session_state['editor']}")
            f_name = st.text_input("Farmer Name")
            woreda = st.text_input("Woreda")
            phone = st.text_input("Phone")
            audio = st.file_uploader("Audio", type=['mp3','wav','m4a'])
            if st.form_submit_button("Save"):
                if f_name and woreda:
                    db = SessionLocal()
                    db.add(Farmer(name=f_name, woreda=woreda, phone=phone, 
                                  audio_data=to_b64(audio), registered_by=st.session_state["editor"]))
                    db.commit(); db.close()
                    st.success("✅ Saved!")

# --- 6. PAGE: ADMIN DASHBOARD ---
elif st.session_state["page"] == "Data":
    st.button("⬅️ Home", on_click=lambda: nav("Home"))
    
    if not st.session_state["auth"]:
        pwd = st.text_input("Admin Passcode", type="password")
        if pwd == "oaf2025": 
            st.session_state["auth"] = True
            st.rerun()
    else:
        db = SessionLocal()
        farmers = db.query(Farmer).all()
        
        if farmers:
            st.subheader("📥 Downloads")
            c1, c2 = st.columns(2)
            
            # --- FIXED EXCEL (CSV with UTF-8 BOM for Amharic Support) ---
            df = pd.DataFrame([{
                "ID": f.id, "Name": f.name, "Woreda": f.woreda, "Phone": f.phone,
                "Editor": f.registered_by, "Date": f.timestamp
            } for f in farmers])
            
            csv_data = df.to_csv(index=False).encode('utf-8-sig') # utf-8-sig makes it work in Excel
            c1.download_button("📥 Download Excel (CSV)", csv_data, "Survey_Data.csv", "text/csv")
            
            # --- FIXED ZIP GENERATION ---
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                a_count = 0
                for f in farmers:
                    if f.audio_data:
                        try:
                            # Cleanup name for filename safety
                            safe_name = "".join([c for c in f.name if c.isalnum() or c in (' ', '_')]).rstrip()
                            zf.writestr(f"ID_{f.id}_{safe_name}.mp3", base64.b64decode(f.audio_data))
                            a_count += 1
                        except: pass
            
            if a_count > 0:
                c2.download_button(f"🎤 Download {a_count} Audios (ZIP)", zip_buffer.getvalue(), "Audios.zip", "application/zip")
            else:
                c2.warning("No audio files found.")

            st.divider()
            
            # --- MANAGE BY ID ---
            for f in farmers:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3,1,1])
                    col1.write(f"**ID: {f.id}** | {f.name} | {f.woreda}")
                    
                    if col2.button("✏️ Edit", key=f"e{f.id}"): st.session_state["edit_id"] = f.id
                    if col3.button("🗑️ Delete", key=f"d{f.id}"):
                        db.delete(f); db.commit(); st.rerun()
                    
                    if st.session_state["edit_id"] == f.id:
                        with st.form(f"f{f.id}"):
                            u_name = st.text_input("New Name", value=f.name)
                            if st.form_submit_button("Update"):
                                f.name = u_name
                                db.commit(); st.session_state["edit_id"] = None; st.rerun()

            st.divider()
            if st.button("⚠️ DELETE ALL RECORDS", type="primary"):
                db.query(Farmer).delete(); db.commit(); st.rerun()
        else:
            st.info("No records.")
        db.close()
