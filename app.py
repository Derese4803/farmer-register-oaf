import streamlit as st
import pandas as pd
import base64
import zipfile
from io import BytesIO
from database import SessionLocal
from models import Farmer, Woreda, Kebele, create_tables

# --- INITIAL SETUP ---
st.set_page_config(page_title="2025 Amhara Survey", page_icon="🌾", layout="wide")
create_tables()

# Initialize session states
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Home"
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "editor_name" not in st.session_state:
    st.session_state["editor_name"] = None
if "editing_id" not in st.session_state:
    st.session_state["editing_id"] = None

def to_base64(uploaded_file):
    if uploaded_file:
        return base64.b64encode(uploaded_file.getvalue()).decode()
    return None

# --- PAGE: HOME ---
def home_page():
    st.title("🌾 Amhara Planting Survey 2025")
    if st.session_state["editor_name"]:
        st.success(f"👤 Active Editor: **{st.session_state['editor_name']}**")
    
    st.divider()
    col1, col2 = st.columns(2)
    
    if col1.button("📝 NEW REGISTRATION", use_container_width=True, type="primary"):
        st.session_state["current_page"] = "Register"
        st.rerun()
    if col2.button("📊 VIEW & MANAGE DATA", use_container_width=True):
        st.session_state["current_page"] = "Download"
        st.rerun()

# --- PAGE: REGISTRATION ---
def register_page():
    if st.button("⬅️ Back to Home"):
        st.session_state["current_page"] = "Home"
        st.rerun()

    st.header("📝 Farmer Registration")

    # 1. Editor Login (Once)
    if not st.session_state["editor_name"]:
        with st.container(border=True):
            st.subheader("Editor Login / የመዝጋቢው መለያ")
            name_input = st.text_input("Enter Your Name (Registered By)")
            if st.button("Login & Start"):
                if name_input.strip():
                    st.session_state["editor_name"] = name_input.strip()
                    st.rerun()
                else:
                    st.error("Please enter your name.")
        return

    # 2. Registration Form
    db = SessionLocal()
    try:
        woreda_objs = db.query(Woreda).order_by(Woreda.name).all()
        w_list = [w.name for w in woreda_objs]
        
        with st.form(key="farmer_reg_form", clear_on_submit=True):
            st.write(f"Logged in as: **{st.session_state['editor_name']}**")
            f_name = st.text_input("Farmer Full Name / የገበሬው ሙሉ ስም")
            woreda = st.text_input("Woreda / ወረዳ")
            kebele = st.text_input("Kebele / ቀበሌ")
            phone = st.text_input("Phone / ስልክ")
            audio = st.file_uploader("Upload Audio", type=['mp3', 'wav', 'm4a'])
            
            if st.form_submit_button("Save Registration"):
                if f_name and woreda:
                    new_f = Farmer(name=f_name, woreda=woreda, kebele=kebele, phone=phone, 
                                   audio_data=to_base64(audio), registered_by=st.session_state["editor_name"])
                    db.add(new_f); db.commit()
                    st.success("✅ Saved Successfully!")
                else:
                    st.error("Name and Woreda are required.")
    finally:
        db.close()

# --- PAGE: VIEW / EDIT / DELETE / DOWNLOAD ---
def download_page():
    if st.button("⬅️ Back to Home"):
        st.session_state["current_page"] = "Home"
        st.rerun()

    st.header("📊 Data Management Center")
    
    # Passcode Gate
    if not st.session_state["authenticated"]:
        passcode = st.text_input("Enter Admin Passcode", type="password")
        if passcode == "oaf2025":
            st.session_state["authenticated"] = True
            st.rerun()
        return

    db = SessionLocal()
    try:
        farmers = db.query(Farmer).order_by(Farmer.id.desc()).all()
        if not farmers:
            st.info("No records found.")
            return

        # DATA MANAGEMENT TABLE
        for f in farmers:
            with st.expander(f"🆔 ID: {f.id} | 👤 {f.name} ({f.woreda})"):
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.write(f"**Phone:** {f.phone} | **By:** {f.registered_by} | **Date:** {f.timestamp.strftime('%Y-%m-%d')}")
                
                # Edit Logic
                if col2.button("✏️ Edit", key=f"edit_{f.id}"):
                    st.session_state["editing_id"] = f.id
                
                # Delete Logic
                if col3.button("🗑️ Delete", key=f"del_{f.id}", type="secondary"):
                    db.delete(f)
                    db.commit()
                    st.rerun()

                # If Editing this specific ID
                if st.session_state["editing_id"] == f.id:
                    with st.form(key=f"f_edit_{f.id}"):
                        edit_name = st.text_input("Edit Name", value=f.name)
                        edit_phone = st.text_input("Edit Phone", value=f.phone)
                        if st.form_submit_button("Update Record"):
                            f.name = edit_name
                            f.phone = edit_phone
                            db.commit()
                            st.session_state["editing_id"] = None
                            st.rerun()

        st.divider()
        st.subheader("📥 Export Data")
        c1, c2 = st.columns(2)
        
        # Download Excel (CSV)
        df = pd.DataFrame([{
            "ID": f.id, "Name": f.name, "Woreda": f.woreda, "Kebele": f.kebele, 
            "Phone": f.phone, "Registered By": f.registered_by, "Date": f.timestamp
        } for f in farmers])
        c1.download_button("📥 Download Excel (CSV)", df.to_csv(index=False).encode('utf-8-sig'), "Survey_Data.csv", "text/csv")
        
        # Download Audio ZIP
        zip_buf = BytesIO()
        with zipfile.ZipFile(zip_buf, "a", zipfile.ZIP_DEFLATED) as zf:
            a_count = 0
            for f in farmers:
                if f.audio_data:
                    zf.writestr(f"ID_{f.id}_{f.name}.mp3", base64.b64decode(f.audio_data))
                    a_count += 1
        if a_count > 0:
            c2.download_button(f"🎤 Download {a_count} Audios (ZIP)", zip_buf.getvalue(), "Audios.zip", "application/zip")

    finally:
        db.close()

# --- MAIN ---
def main():
    if st.session_state["current_page"] == "Home": home_page()
    elif st.session_state["current_page"] == "Register": register_page()
    elif st.session_state["current_page"] == "Download": download_page()

if __name__ == "__main__":
    main()
