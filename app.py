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
        st.info(f"👤 Current Editor: **{st.session_state['editor_name']}**")
    
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

    # LOGIN LOGIC: Ask for name ONLY ONCE
    if not st.session_state["editor_name"]:
        with st.container(border=True):
            st.subheader("Editor Login")
            name_input = st.text_input("Enter Your Name to Begin")
            if st.button("Start Registering"):
                if name_input.strip():
                    st.session_state["editor_name"] = name_input.strip()
                    st.rerun()
                else:
                    st.error("Please enter a name.")
        return

    # REGISTRATION FORM
    db = SessionLocal()
    try:
        woreda_objs = db.query(Woreda).order_by(Woreda.name).all()
        woreda_list = [w.name for w in woreda_objs]
        
        with st.form(key="farmer_reg_form", clear_on_submit=True):
            st.write(f"Logged in as: **{st.session_state['editor_name']}**")
            farmer_name = st.text_input("Farmer Full Name")
            
            w_col1, w_col2 = st.columns(2)
            sel_woreda = w_col1.selectbox("Select Woreda", ["None"] + woreda_list)
            type_woreda = w_col2.text_input("Or Type New Woreda")
            final_woreda = type_woreda.strip() if type_woreda.strip() else (None if sel_woreda == "None" else sel_woreda)

            phone = st.text_input("Phone Number")
            audio = st.file_uploader("Upload Audio", type=['mp3', 'wav'])
            
            if st.form_submit_button("Save Registration"):
                if farmer_name and final_woreda:
                    new_f = Farmer(name=farmer_name, woreda=final_woreda, phone=phone, 
                                   audio_data=to_base64(audio), registered_by=st.session_state["editor_name"])
                    db.add(new_f); db.commit()
                    st.success("✅ Saved Successfully!")
    finally:
        db.close()

# --- PAGE: VIEW/EDIT/DELETE ---
def download_page():
    if st.button("⬅️ Back to Home"):
        st.session_state["current_page"] = "Home"
        st.rerun()

    st.header("📊 Data Management")
    
    # PASSCODE PROTECTION
    if not st.session_state["authenticated"]:
        passcode = st.text_input("Enter Admin Passcode", type="password")
        if passcode == "oaf2025":
            st.session_state["authenticated"] = True
            st.rerun()
        return

    db = SessionLocal()
    try:
        farmers = db.query(Farmer).all()
        if not farmers:
            st.info("No records found.")
            return

        # DATA TABLE DISPLAY
        for f in farmers:
            with st.expander(f"👤 {f.name} - {f.woreda}"):
                col1, col2, col3 = st.columns([2,1,1])
                col1.write(f"**Phone:** {f.phone} | **Editor:** {f.registered_by}")
                
                # EDIT BUTTON
                if col2.button("✏️ Edit", key=f"edit_{f.id}"):
                    st.session_state["editing_id"] = f.id
                
                # DELETE BUTTON
                if col3.button("🗑️ Delete", key=f"del_{f.id}", type="secondary"):
                    db.delete(f); db.commit()
                    st.rerun()

                # SHOW EDIT FORM IF CLICKED
                if st.session_state["editing_id"] == f.id:
                    with st.form(key=f"edit_form_{f.id}"):
                        new_name = st.text_input("New Name", value=f.name)
                        new_woreda = st.text_input("New Woreda", value=f.woreda)
                        if st.form_submit_button("Update"):
                            f.name = new_name
                            f.woreda = new_woreda
                            db.commit()
                            st.session_state["editing_id"] = None
                            st.rerun()
        
        st.divider()
        # DOWNLOAD SECTION
        df = pd.DataFrame([{"ID": f.id, "Name": f.name, "Woreda": f.woreda, "Editor": f.registered_by} for f in farmers])
        st.download_button("📥 Download CSV", df.to_csv(index=False), "data.csv", "text/csv")
        
    finally:
        db.close()

# --- MAIN ENGINE ---
def main():
    if st.session_state["current_page"] == "Home": home_page()
    elif st.session_state["current_page"] == "Register": register_page()
    elif st.session_state["current_page"] == "Download": download_page()

if __name__ == "__main__":
    main()
