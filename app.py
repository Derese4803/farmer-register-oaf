import streamlit as st
import pandas as pd
import base64
import zipfile
from io import BytesIO
from database import SessionLocal
from models import Farmer, create_tables

# --- APP CONFIG ---
st.set_page_config(page_title="Amhara Survey 2025", layout="wide", page_icon="🌾")
create_tables()

# Initialize Session States
if "page" not in st.session_state: st.session_state["page"] = "Home"
if "auth" not in st.session_state: st.session_state["auth"] = False
if "editor" not in st.session_state: st.session_state["editor"] = None
if "edit_id" not in st.session_state: st.session_state["edit_id"] = None

def to_b64(file):
    return base64.b64encode(file.getvalue()).decode() if file else None

def nav(p):
    st.session_state["page"] = p
    st.rerun()

# --- HOME PAGE ---
if st.session_state["page"] == "Home":
    st.title("🌾 Amhara Survey Management")
    if st.session_state["editor"]:
        st.success(f"👤 Active Editor: **{st.session_state['editor']}**")
    
    st.divider()
    col1, col2 = st.columns(2)
    if col1.button("📝 NEW REGISTRATION", use_container_width=True, type="primary"): nav("Reg")
    if col2.button("📊 MANAGE DATA & DOWNLOADS", use_container_width=True): nav("Data")

# --- REGISTRATION PAGE ---
elif st.session_state["page"] == "Reg":
    st.button("⬅️ Back to Home", on_click=lambda: nav("Home"))
    
    if not st.session_state["editor"]:
        with st.container(border=True):
            st.subheader("Editor Login (One-Time)")
            name = st.text_input("Enter Your Name / የመዝጋቢ ስም")
            if st.button("Start Registering"):
                if name: 
                    st.session_state["editor"] = name
                    st.rerun()
    else:
        st.header(f"Register Farmer (Editor: {st.session_state['editor']})")
        with st.form("reg_form", clear_on_submit=True):
            f_name = st.text_input("Farmer Full Name")
            woreda = st.text_input("Woreda")
            phone = st.text_input("Phone Number")
            audio = st.file_uploader("🎤 Upload Audio Recording", type=['mp3','wav','m4a'])
            if st.form_submit_button("Submit Registration"):
                if f_name and woreda:
                    db = SessionLocal()
                    new_f = Farmer(name=f_name, woreda=woreda, phone=phone, 
                                   audio_data=to_b64(audio), registered_by=st.session_state["editor"])
                    db.add(new_f); db.commit(); db.close()
                    st.success("✅ Record Saved Successfully!")
                else:
                    st.error("Name and Woreda are required.")

# --- DATA MANAGEMENT & DOWNLOADS ---
elif st.session_state["page"] == "Data":
    st.button("⬅️ Back to Home", on_click=lambda: nav("Home"))
    
    if not st.session_state["auth"]:
        pwd = st.text_input("Admin Passcode", type="password")
        if pwd == "oaf2025": 
            st.session_state["auth"] = True
            st.rerun()
    else:
        db = SessionLocal()
        farmers = db.query(Farmer).all()
        
        st.header("📊 Management & Exports")
        
        if farmers:
            # --- DOWNLOAD SECTION ---
            st.subheader("📥 Bulk Downloads")
            dl_col1, dl_col2 = st.columns(2)
            
            # 1. Excel/CSV Download
            df = pd.DataFrame([{
                "ID": f.id, "Name": f.name, "Woreda": f.woreda, 
                "Phone": f.phone, "Editor": f.registered_by, "Date": f.timestamp
            } for
