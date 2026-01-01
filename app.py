import streamlit as st
import pandas as pd
import base64
import zipfile
import datetime
from io import BytesIO
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base

# --- 1. DATABASE & MODELS ---
Base = declarative_base()

class Farmer(Base):
    __tablename__ = 'farmers'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    name = Column(String, nullable=False)
    woreda = Column(String)
    kebele = Column(String)
    phone = Column(String)
    audio_data = Column(Text)  # Stores audio as base64 string
    registered_by = Column(String)

# Connect to SQLite
engine = create_engine("sqlite:///./survey_2025.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

# --- 2. HELPER FUNCTIONS ---
def to_b64(file):
    if file:
        return base64.b64encode(file.getvalue()).decode()
    return None

# --- 3. APP CONFIG & SESSION STATE ---
st.set_page_config(page_title="Amhara Survey 2025", layout="wide", page_icon="🌾")

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
    st.button("⬅️ Back to Home", on_click=lambda: nav("Home"))
    
    # Login Section (Once per session)
    if not st.session_state["editor"]:
        with st.container(border=True):
            st.subheader("Editor Login")
            name_input = st.text_input("Enter Your Name / የመዝጋቢ ስም")
            if st.button("Start Registering"):
                if name_input.strip():
                    st.session_state["editor"] = name_input.strip()
                    st.rerun()
                else:
                    st.error("Name is required.")
    else:
        # Registration Form
        st.header(f"New Registration (By: {st.session_state['editor']})")
        with st.form("main_reg_form", clear_on_submit=True):
            f_name = st.text_input("Farmer Full Name")
            woreda = st.text_input("Woreda")
            kebele = st.text_input("Kebele")
            phone = st.text_input("Phone Number")
            audio = st.file_uploader("🎤 Upload Audio Recording", type=['mp3','wav','m4a'])
            
            if st.form_submit_button("Save Record"):
                if f_name and woreda:
                    db = SessionLocal()
                    new_f = Farmer(
                        name=f_name, woreda=woreda, kebele=kebele, phone=phone, 
                        audio_data=to_b64(audio), registered_by=st.session_state["editor"]
                    )
                    db.add(new_f); db.commit(); db.close()
                    st.success("✅ Record Saved Successfully!")
                else:
                    st.error("Farmer Name and Woreda are required.")

# --- 6. PAGE: ADMIN DASHBOARD (Manage & Downloads) ---
elif st.session_state["page"] == "Data":
    st.button("⬅️ Back to Home", on_click=lambda: nav("Home"))
    
    # Admin Security
    if not st.session_state["auth"]:
        passcode = st.text_input("Enter Admin Passcode", type="password")
        if passcode == "oaf2025": 
            st.session_state["auth"] = True
            st.rerun()
    else:
        st.header("📊 Management & Exports")
        db = SessionLocal()
        farmers = db.query(Farmer).order_by(Farmer.id.desc()).all()
        
        if farmers:
            # --- BULK DOWNLOADS ---
            c1, c2 = st.columns(2)
            
            # Excel Download
            df = pd.DataFrame([{
                "ID": f.id, "Name": f.name, "Woreda": f.woreda, "Kebele": f.kebele,
                "Phone": f.phone, "Editor": f.registered_by, "Date": f.timestamp
            } for f in farmers])
            c1.download_button("📥 Download Excel (CSV)", df.to_csv(index=False).encode('utf-8-sig'), "Survey_Data.csv", "text/csv", use_container_width=True)
            
            # Audio ZIP Download
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zf:
                count = 0
                for f in farmers:
                    if f.audio_data:
                        zf.writestr(f"ID_{f.id}_{f.name}.mp3", base64.b64decode(f.audio_data))
                        count += 1
            if count > 0:
                c2.download_button(f"🎤 Download {count} Audios (ZIP)", zip_buffer.getvalue(), "Audios.zip", use_container_width=True)
            
            st.divider()
            
            # --- RECORD MANAGEMENT (Edit/Delete) ---
            st.subheader("📝 Individual Records")
            for f in farmers:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    col1.write(f"**ID: {f.id}** | {f.name} ({f.woreda}) | 👤 {f.registered_by}")
                    
                    if col2.button("✏️ Edit", key=f"e_{f.id}"):
                        st.session_state["edit_id"] = f.id
                    
                    if col3.button("🗑️ Delete", key=f"d_{f.id}"):
                        db.delete(f); db.commit()
                        st.rerun()
                    
                    # Inline Edit Form
                    if st.session_state["edit_id"] == f.id:
                        with st.form(f"edit_form_{f.id}"):
                            new_name = st.text_input("Update Name", value=f.name)
                            new_woreda = st.text_input("Update Woreda", value=f.woreda)
                            if st.form_submit_button("Confirm Update"):
                                f.name = new_name
                                f.woreda = new_woreda
                                db.commit()
                                st.session_state["edit_id"] = None
                                st.rerun()

            st.divider()
            # DELETE ALL BUTTON
            with st.expander("🚨 Advanced: Delete All Records"):
                if st.button("CONFIRM: CLEAR ENTIRE DATABASE", type="primary"):
                    db.query(Farmer).delete()
                    db.commit()
                    st.rerun()
        else:
            st.info("No records found.")
        db.close()
