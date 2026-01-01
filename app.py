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

# Initialize Navigation
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Home"

def nav(page):
    st.session_state["current_page"] = page
    st.rerun()

def to_base64(uploaded_file):
    if uploaded_file:
        return base64.b64encode(uploaded_file.getvalue()).decode()
    return None

# --- PAGE: HOME ---
def home_page():
    st.title("🌾 Amhara Planting Survey 2025")
    st.divider()
    col1, col2 = st.columns(2)
    if col1.button("📝 NEW REGISTRATION", use_container_width=True, type="primary"):
        nav("Register")
    if col2.button("📊 VIEW & DOWNLOAD DATA", use_container_width=True):
        nav("Download")

# --- PAGE: REGISTRATION (FIXED) ---
def register_page():
    if st.button("⬅️ Back to Home"):
        nav("Home")
        
    st.header("📝 Farmer Registration")
    db = SessionLocal()
    
    try:
        # Get list of woredas
        woreda_objs = db.query(Woreda).order_by(Woreda.name).all()
        woreda_list = [w.name for w in woreda_objs]
        
        # Use a single form for everything
        with st.form(key="farmer_reg_form_v1", clear_on_submit=True):
            name = st.text_input("Farmer Full Name / የገበሬው ሙሉ ስም", key="reg_name_input")
            
            st.markdown("---")
            st.subheader("📍 Location Details")
            
            # Woreda Selection
            w_col1, w_col2 = st.columns(2)
            sel_woreda = w_col1.selectbox(
                "Select Existing Woreda / ካለ ይምረጡ", 
                options=["None / አዲስ ጻፍ"] + woreda_list,
                key="reg_woreda_select"
            )
            type_woreda = w_col2.text_input("Or Type New Woreda / ወይም አዲስ ወረዳ ይጻፉ", key="reg_woreda_type")
            
            # Determine Final Woreda
            final_woreda = type_woreda.strip() if type_woreda.strip() else (None if sel_woreda == "None / አዲስ ጻፍ" else sel_woreda)

            # Kebele Selection
            k_col1, k_col2 = st.columns(2)
            
            # Logic for fetching kebeles based on selected woreda
            kebeles_for_woreda = []
            if sel_woreda != "None / አዲስ ጻፍ":
                w_obj = db.query(Woreda).filter(Woreda.name == sel_woreda).first()
                if w_obj:
                    kebeles_for_woreda = [k.name for k in w_obj.kebeles]

            sel_kebele = k_col1.selectbox(
                "Select Existing Kebele / ቀበሌ ይምረጡ", 
                options=["None / አዲስ ጻፍ"] + kebeles_for_woreda,
                key="reg_kebele_select"
            )
            type_kebele = k_col2.text_input("Or Type New Kebele / ወይም አዲስ ቀበሌ ይጻፉ", key="reg_kebele_type")
            
            # Determine Final Kebele
            final_kebele = type_kebele.strip() if type_kebele.strip() else (None if sel_kebele == "None / አዲስ ጻፍ" else sel_kebele)

            st.markdown("---")
            phone = st.text_input("Phone Number / ስልክ ቁጥር", key="reg_phone_input")
            audio = st.file_uploader("🎤 Upload Audio Recording / ድምፅ ይጫኑ", type=['mp3', 'wav', 'm4a'], key="reg_audio_uploader")
            
            # EVERY FORM MUST HAVE THIS BUTTON TO WORK
            submit_btn = st.form_submit_button("Submit Registration")
            
            if submit_btn:
                if name and final_woreda and final_kebele:
                    # 1. Ensure Woreda is in DB
                    target_w = db.query(Woreda).filter(Woreda.name == final_woreda).first()
                    if not target_w:
                        target_w = Woreda(name=final_woreda)
                        db.add(target_w)
                        db.commit()
                        db.refresh(target_w)
                    
                    # 2. Ensure Kebele is in DB
                    target_k = db.query(Kebele).filter(Kebele.name == final_kebele, Kebele.woreda_id == target_w.id).first()
                    if not target_k:
                        target_k = Kebele(name=final_kebele, woreda_id=target_w.id)
                        db.add(target_k)
                        db.commit()
                    
                    # 3. Save Farmer Record
                    new_farmer = Farmer(
                        name=name,
                        woreda=final_woreda,
                        kebele=final_kebele,
                        phone=phone,
                        audio_data=to_base64(audio),
                        registered_by="System"
                    )
                    db.add(new_farmer)
                    db.commit()
                    st.success(f"✅ Registered: {name} in {final_kebele}, {final_woreda}")
                else:
                    st.error("⚠️ Please fill in Name, Woreda, and Kebele!")
                    
    finally:
        db.close()

# --- PAGE: DOWNLOAD ---
def download_page():
    if st.button("⬅️ Back to Home"):
        nav("Home")
    st.header("📊 Survey Records")
    db = SessionLocal()
    try:
        farmers = db.query(Farmer).all()
        if farmers:
            df = pd.DataFrame([{
                "ID": f.id, "Farmer": f.name, "Woreda": f.woreda, 
                "Kebele": f.kebele, "Phone": f.phone, "Date": f.timestamp
            } for f in farmers])
            st.dataframe(df, use_container_width=True)
            
            # Export
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Download Data (CSV)", csv, "Amhara_Survey.csv", "text/csv", key="dl_csv_btn")
        else:
            st.info("No records found.")
    finally:
        db.close()

# --- MAIN ---
def main():
    page = st.session_state["current_page"]
    if page == "Home":
        home_page()
    elif page == "Register":
        register_page()
    elif page == "Download":
        download_page()

if __name__ == "__main__":
    main()
