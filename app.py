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

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Home"

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
        st.session_state["current_page"] = "Register"
        st.rerun()
    if col2.button("📊 VIEW & DOWNLOAD DATA", use_container_width=True):
        st.session_state["current_page"] = "Download"
        st.rerun()

# --- PAGE: REGISTRATION ---
def register_page():
    if st.button("⬅️ Back to Home"):
        st.session_state["current_page"] = "Home"
        st.rerun()
        
    st.header("📝 Farmer Registration")
    db = SessionLocal()
    
    try:
        woreda_objs = db.query(Woreda).order_by(Woreda.name).all()
        woreda_list = [w.name for w in woreda_objs]
        
        with st.form(key="farmer_reg_v4", clear_on_submit=True):
            editor_name = st.text_input("Editor Name / የመዝጋቢው ስም", key="editor_val")
            st.divider()
            
            farmer_name = st.text_input("Farmer Full Name / የገበሬው ሙሉ ስም", key="f_val")
            
            st.write("📍 **Location Details**")
            w_col1, w_col2 = st.columns(2)
            sel_woreda = w_col1.selectbox("Select Woreda", ["None / አዲስ ጻፍ"] + woreda_list, key="ws")
            type_woreda = w_col2.text_input("Or Type New Woreda", key="wt")
            final_woreda = type_woreda.strip() if type_woreda.strip() else (None if sel_woreda == "None / አዲስ ጻፍ" else sel_woreda)

            k_col1, k_col2 = st.columns(2)
            kb_list = []
            if final_woreda and sel_woreda != "None / አዲስ ጻፍ":
                w_obj = db.query(Woreda).filter(Woreda.name == final_woreda).first()
                if w_obj: kb_list = [k.name for k in w_obj.kebeles]
            
            sel_kebele = k_col1.selectbox("Select Kebele", ["None / አዲስ ጻፍ"] + kb_list, key="ks")
            type_kebele = k_col2.text_input("Or Type New Kebele", key="kt")
            final_kebele = type_kebele.strip() if type_kebele.strip() else (None if sel_kebele == "None / አዲስ ጻፍ" else sel_kebele)

            phone = st.text_input("Phone Number / ስልክ ቁጥር", key="ph")
            audio = st.file_uploader("🎤 Upload Audio Recording", type=['mp3', 'wav', 'm4a'], key="aud")
            
            if st.form_submit_button("Save Registration"):
                if farmer_name and final_woreda and final_kebele and editor_name:
                    # Sync Woreda/Kebele
                    w_obj = db.query(Woreda).filter(Woreda.name == final_woreda).first()
                    if not w_obj:
                        w_obj = Woreda(name=final_woreda)
                        db.add(w_obj); db.commit(); db.refresh(w_obj)
                    k_obj = db.query(Kebele).filter(Kebele.name == final_kebele, Kebele.woreda_id == w_obj.id).first()
                    if not k_obj:
                        db.add(Kebele(name=final_kebele, woreda_id=w_obj.id)); db.commit()
                    
                    # Save Farmer
                    new_f = Farmer(name=farmer_name, woreda=final_woreda, kebele=final_kebele,
                                   phone=phone, audio_data=to_base64(audio), registered_by=editor_name)
                    db.add(new_f); db.commit()
                    st.success(f"✅ Saved! Registered by: {editor_name}")
                else:
                    st.error("⚠️ All fields (Name, Woreda, Kebele, Editor) are required.")
    finally:
        db.close()

# --- PAGE: DOWNLOAD (PASSCODE PROTECTED) ---
def download_page():
    if st.button("⬅️ Back to Home"):
        st.session_state["current_page"] = "Home"
        st.rerun()
        
    st.header("📊 Admin Data Access")
    passcode = st.text_input("Enter Passcode to View Data", type="password", key="p_gate")
    
    if passcode == "oaf2025":
        db = SessionLocal()
        try:
            farmers = db.query(Farmer).all()
            if farmers:
                df = pd.DataFrame([{
                    "ID": f.id, "Farmer": f.name, "Woreda": f.woreda, "Kebele": f.kebele, 
                    "Phone": f.phone, "Registered By": f.registered_by, "Date": f.timestamp
                } for f in farmers])
                st.dataframe(df, use_container_width=True)
                
                c1, c2 = st.columns(2)
                c1.download_button("📥 Download CSV", df.to_csv(index=False).encode('utf-8-sig'), "Survey.csv", "text/csv")
                
                # Audio ZIP
                buf = BytesIO()
                with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED) as zf:
                    count = 0
                    for f in farmers:
                        if f.audio_data:
                            zf.writestr(f"{f.id}_{f.name.replace(' ','_')}.mp3", base64.b64decode(f.audio_data))
                            count += 1
                if count > 0:
                    c2.download_button(f"🎤 Download {count} Audios (ZIP)", buf.getvalue(), "Audios.zip", "application/zip")
            else:
                st.info("No records yet.")
        finally:
            db.close()
    elif passcode != "":
        st.error("❌ Incorrect Passcode")

# --- MAIN ---
def main():
    pg = st.session_state["current_page"]
    if pg == "Home": home_page()
    elif pg == "Register": register_page()
    elif pg == "Download": download_page()

if __name__ == "__main__":
    main()
