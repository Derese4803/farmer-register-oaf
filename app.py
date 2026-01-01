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

def nav(page):
    st.session_state["current_page"] = page
    st.rerun()

def to_base64(uploaded_file):
    if uploaded_file:
        return base64.b64encode(uploaded_file.getvalue()).decode()
    return None

# --- PAGES ---
def home_page():
    st.title("🌾 Amhara Planting Survey 2025")
    st.divider()
    col1, col2 = st.columns(2)
    if col1.button("📝 NEW REGISTRATION", use_container_width=True, type="primary"):
        nav("Register")
    if col2.button("📊 VIEW & DOWNLOAD DATA", use_container_width=True):
        nav("Download")

def register_page():
    st.button("⬅️ Back to Home", on_click=lambda: nav("Home"))
    st.header("📝 Farmer Registration")
    db = SessionLocal()
    
    try:
        # Fetch Existing Woredas for the dropdown
        woreda_list = [w.name for w in db.query(Woreda).order_by(Woreda.name).all()]
        
        with st.form("reg_form", clear_on_submit=True):
            name = st.text_input("Farmer Full Name / የገበሬው ሙሉ ስም")
            
            # --- WOREDA SECTION ---
            st.write("📍 **Woreda / ወረዳ**")
            w_col1, w_col2 = st.columns(2)
            sel_woreda = w_col1.selectbox("Select Existing / ካለ ይምረጡ", ["None / አዲስ ጻፍ"] + woreda_list)
            type_woreda = w_col2.text_input("Or Type New / ወይም አዲስ እዚህ ይጻፉ")
            
            # Decide Woreda Name
            final_woreda = type_woreda.strip() if type_woreda else (None if sel_woreda == "None / አዲስ ጻፍ" else sel_woreda)

            # --- KEBELE SECTION ---
            st.write("📍 **Kebele / ቀበሌ**")
            k_col1, k_col2 = st.columns(2)
            
            existing_kebeles = []
            if final_woreda and sel_woreda != "None / አዲስ ጻፍ":
                w_obj = db.query(Woreda).filter(Woreda.name == final_woreda).first()
                if w_obj:
                    existing_kebeles = [k.name for k in w_obj.kebeles]
            
            sel_kebele = k_col1.selectbox("Select Existing / ካለ ይምረጡ", ["None / አዲስ ጻፍ"] + existing_kebeles)
            type_kebele = k_col2.text_input("Or Type New / ወይም አዲስ እዚህ ይጻፉ")
            
            # Decide Kebele Name
            final_kebele = type_kebele.strip() if type_kebele else (None if sel_kebele == "None / አዲስ ጻፍ" else sel_kebele)

            phone = st.text_input("Phone Number / ስልክ ቁጥር")
            audio = st.file_uploader("🎤 Upload Audio Recording / ድምፅ ይጫኑ", type=['mp3', 'wav', 'm4a'])
            
            if st.form_submit_button("Save Registration / መረጃውን መዝግብ"):
                if name and final_woreda and final_kebele:
                    # 1. Check/Save Woreda
                    w_obj = db.query(Woreda).filter(Woreda.name == final_woreda).first()
                    if not w_obj:
                        w_obj = Woreda(name=final_woreda)
                        db.add(w_obj)
                        db.commit()
                        db.refresh(w_obj)
                    
                    # 2. Check/Save Kebele
                    k_obj = db.query(Kebele).filter(Kebele.name == final_kebele, Kebele.woreda_id == w_obj.id).first()
                    if not k_obj:
                        db.add(Kebele(name=final_kebele, woreda_id=w_obj.id))
                        db.commit()
                    
                    # 3. Save Farmer Record
                    new_farmer = Farmer(
                        name=name,
                        woreda=final_woreda,
                        kebele=final_kebele,
                        phone=phone,
                        audio_data=to_base64(audio),
                        registered_by="Open Access"
                    )
                    db.add(new_farmer)
                    db.commit()
                    st.success(f"✅ Successfully saved {name}!")
                else:
                    st.error("⚠️ Please provide Name, Woreda, and Kebele.")
    finally:
        db.close()

def download_page():
    st.button("⬅️ Back to Home", on_click=lambda: nav("Home"))
    st.header("📊 Recorded Data")
    db = SessionLocal()
    try:
        farmers = db.query(Farmer).all()
        if farmers:
            df = pd.DataFrame([{
                "ID": f.id, "Farmer": f.name, "Woreda": f.woreda, 
                "Kebele": f.kebele, "Phone": f.phone, "Date": f.timestamp
            } for f in farmers])
            
            st.dataframe(df, use_container_width=True)
            
            # ZIP Audios
            buf = BytesIO()
            with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED) as zf:
                for f in farmers:
                    if f.audio_data:
                        zf.writestr(f"{f.name}_{f.kebele}.mp3", base64.b64decode(f.audio_data))
            
            c1, c2 = st.columns(2)
            c1.download_button("📥 Download Excel (CSV)", df.to_csv(index=False).encode('utf-8-sig'), "Survey_Data.csv", use_container_width=True)
            c2.download_button("🎤 Download All Audios (ZIP)", buf.getvalue(), "Farmer_Audios.zip", use_container_width=True)
        else:
            st.info("No records found yet.")
    finally:
        db.close()

# --- MAIN NAVIGATION ---
def main():
    pg = st.session_state["current_page"]
    if pg == "Home":
        home_page()
    elif pg == "Register":
        register_page()
    elif pg == "Download":
        download_page()

if __name__ == "__main__":
    main()
