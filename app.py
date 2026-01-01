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

# --- PAGE: REGISTRATION ---
def register_page():
    if st.button("⬅️ Back to Home"):
        nav("Home")
        
    st.header("📝 Farmer Registration")
    db = SessionLocal()
    
    try:
        woreda_objs = db.query(Woreda).order_by(Woreda.name).all()
        woreda_list = [w.name for w in woreda_objs]
        
        with st.form(key="farmer_reg_form_v1", clear_on_submit=True):
            name = st.text_input("Farmer Full Name / የገበሬው ሙሉ ስም", key="reg_name_input")
            
            st.markdown("---")
            st.subheader("📍 Location Details")
            
            w_col1, w_col2 = st.columns(2)
            sel_woreda = w_col1.selectbox("Select Existing Woreda", options=["None / አዲስ ጻፍ"] + woreda_list, key="reg_woreda_select")
            type_woreda = w_col2.text_input("Or Type New Woreda", key="reg_woreda_type")
            final_woreda = type_woreda.strip() if type_woreda.strip() else (None if sel_woreda == "None / አዲስ ጻፍ" else sel_woreda)

            k_col1, k_col2 = st.columns(2)
            kebeles_for_woreda = []
            if sel_woreda != "None / አዲስ ጻፍ":
                w_obj = db.query(Woreda).filter(Woreda.name == sel_woreda).first()
                if w_obj: kebeles_for_woreda = [k.name for k in w_obj.kebeles]

            sel_kebele = k_col1.selectbox("Select Existing Kebele", options=["None / አዲስ ጻፍ"] + kebeles_for_woreda, key="reg_kebele_select")
            type_kebele = k_col2.text_input("Or Type New Kebele", key="reg_kebele_type")
            final_kebele = type_kebele.strip() if type_kebele.strip() else (None if sel_kebele == "None / አዲስ ጻፍ" else sel_kebele)

            st.markdown("---")
            phone = st.text_input("Phone Number / ስልክ ቁጥር", key="reg_phone_input")
            audio = st.file_uploader("🎤 Upload Audio Recording", type=['mp3', 'wav', 'm4a'], key="reg_audio_uploader")
            
            submit_btn = st.form_submit_button("Submit Registration")
            
            if submit_btn:
                if name and final_woreda and final_kebele:
                    target_w = db.query(Woreda).filter(Woreda.name == final_woreda).first()
                    if not target_w:
                        target_w = Woreda(name=final_woreda)
                        db.add(target_w); db.commit(); db.refresh(target_w)
                    
                    target_k = db.query(Kebele).filter(Kebele.name == final_kebele, Kebele.woreda_id == target_w.id).first()
                    if not target_k:
                        target_k = Kebele(name=final_kebele, woreda_id=target_w.id)
                        db.add(target_k); db.commit()
                    
                    new_farmer = Farmer(
                        name=name, woreda=final_woreda, kebele=final_kebele,
                        phone=phone, audio_data=to_base64(audio), registered_by="System"
                    )
                    db.add(new_farmer); db.commit()
                    st.success(f"✅ Registered: {name}")
                else:
                    st.error("⚠️ Please fill in Name, Woreda, and Kebele!")
    finally:
        db.close()

# --- PAGE: DOWNLOAD (WITH AUDIO ZIP) ---
def download_page():
    if st.button("⬅️ Back to Home"):
        nav("Home")
    st.header("📊 Survey Records & Audio Export")
    db = SessionLocal()
    try:
        farmers = db.query(Farmer).all()
        if farmers:
            # 1. Display Data Table
            df = pd.DataFrame([{
                "ID": f.id, "Farmer": f.name, "Woreda": f.woreda, 
                "Kebele": f.kebele, "Phone": f.phone, "Date": f.timestamp
            } for f in farmers])
            st.dataframe(df, use_container_width=True)
            
            st.divider()
            c1, c2 = st.columns(2)
            
            # 2. Download CSV
            csv = df.to_csv(index=False).encode('utf-8-sig')
            c1.download_button("📥 Download Data (CSV)", csv, "Amhara_Survey_Data.csv", "text/csv", key="dl_csv_btn", use_container_width=True)
            
            # 3. Download Audios as ZIP
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zf:
                audio_count = 0
                for f in farmers:
                    if f.audio_data:
                        # Decode Base64 back to bytes
                        try:
                            audio_bytes = base64.b64decode(f.audio_data)
                            # Create a clean filename
                            clean_name = f.name.replace(" ", "_")
                            filename = f"Audio_{f.id}_{clean_name}_{f.kebele}.mp3"
                            zf.writestr(filename, audio_bytes)
                            audio_count += 1
                        except:
                            continue
            
            if audio_count > 0:
                c2.download_button(
                    label=f"🎤 Download {audio_count} Audios (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="Farmer_Audio_Recordings.zip",
                    mime="application/zip",
                    key="dl_zip_btn",
                    use_container_width=True
                )
            else:
                c2.info("No audio recordings available to download.")
                
        else:
            st.info("No records found.")
    finally:
        db.close()

# --- MAIN ---
def main():
    page = st.session_state["current_page"]
    if page == "Home": home_page()
    elif page == "Register": register_page()
    elif page == "Download": download_page()

if __name__ == "__main__":
    main()
