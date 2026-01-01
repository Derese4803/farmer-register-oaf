import streamlit as st
import pandas as pd
import base64
import zipfile
from io import BytesIO
from database import SessionLocal
from models import Farmer, create_tables

# --- APP CONFIG ---
st.set_page_config(page_title="Amhara Survey 2025", layout="wide")
create_tables()

# Initialize Session States
if "page" not in st.session_state: st.session_state["page"] = "Home"
if "auth" not in st.session_state: st.session_state["auth"] = False
if "editor" not in st.session_state: st.session_state["editor"] = None
if "edit_id" not in st.session_state: st.session_state["edit_id"] = None

def to_b64(file):
    return base64.b64encode(file.getvalue()).decode() if file else None

# --- NAVIGATION ---
def nav(p):
    st.session_state["page"] = p
    st.rerun()

# --- HOME PAGE ---
if st.session_state["page"] == "Home":
    st.title("🌾 Amhara Survey Management")
    if st.session_state["editor"]:
        st.success(f"Logged in as: **{st.session_state['editor']}**")
    
    col1, col2 = st.columns(2)
    if col1.button("📝 Registration Form", use_container_width=True): nav("Reg")
    if col2.button("📊 Manage & Download", use_container_width=True): nav("Data")

# --- REGISTRATION PAGE ---
elif st.session_state["page"] == "Reg":
    if st.button("⬅️ Back"): nav("Home")
    
    # One-time Editor Login
    if not st.session_state["editor"]:
        with st.form("editor_login"):
            name = st.text_input("Enter Editor Name / የመዝጋቢ ስም")
            if st.form_submit_button("Login"):
                if name: 
                    st.session_state["editor"] = name
                    st.rerun()
    else:
        st.header(f"New Record (Editor: {st.session_state['editor']})")
        with st.form("reg_form", clear_on_submit=True):
            f_name = st.text_input("Farmer Name")
            woreda = st.text_input("Woreda")
            phone = st.text_input("Phone")
            audio = st.file_uploader("Audio", type=['mp3','wav'])
            if st.form_submit_button("Save"):
                db = SessionLocal()
                new_f = Farmer(name=f_name, woreda=woreda, phone=phone, 
                               audio_data=to_b64(audio), registered_by=st.session_state["editor"])
                db.add(new_f); db.commit(); db.close()
                st.success("Saved!")

# --- DATA MANAGEMENT PAGE ---
elif st.session_state["page"] == "Data":
    if st.button("⬅️ Back"): nav("Home")
    
    if not st.session_state["auth"]:
        pwd = st.text_input("Admin Passcode", type="password")
        if pwd == "oaf2025": 
            st.session_state["auth"] = True
            st.rerun()
    else:
        db = SessionLocal()
        farmers = db.query(Farmer).all()
        
        st.header("📊 Records Management")
        
        # Danger Zone: Delete All
        with st.expander("🚨 Danger Zone"):
            if st.button("🗑️ DELETE ALL RECORDS", type="primary"):
                db.query(Farmer).delete()
                db.commit()
                st.rerun()

        # Download Buttons
        if farmers:
            c1, c2 = st.columns(2)
            df = pd.DataFrame([{"ID": f.id, "Name": f.name, "Woreda": f.woreda, "Editor": f.registered_by} for f in farmers])
            c1.download_button("📥 Download Excel (CSV)", df.to_csv(index=False), "survey.csv")
            
            buf = BytesIO()
            with zipfile.ZipFile(buf, "a") as zf:
                for f in farmers:
                    if f.audio_data:
                        zf.writestr(f"{f.id}_{f.name}.mp3", base64.b64decode(f.audio_data))
            c2.download_button("🎤 Download Audio (ZIP)", buf.getvalue(), "audios.zip")

        # Record List with ID Delete & Edit
        for f in farmers:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.write(f"**ID: {f.id}** | {f.name} ({f.woreda})")
                
                if col2.button("✏️ Edit", key=f"e_{f.id}"):
                    st.session_state["edit_id"] = f.id
                
                if col3.button("🗑️ Delete", key=f"d_{f.id}"):
                    db.delete(f); db.commit()
                    st.rerun()
                
                if st.session_state["edit_id"] == f.id:
                    with st.form(f"form_{f.id}"):
                        u_name = st.text_input("Name", value=f.name)
                        u_woreda = st.text_input("Woreda", value=f.woreda)
                        if st.form_submit_button("Update"):
                            f.name = u_name
                            f.woreda = u_woreda
                            db.commit()
                            st.session_state["edit_id"] = None
                            st.rerun()
        db.close()
