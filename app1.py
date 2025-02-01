import streamlit as st
import pandas as pd
from PIL import Image
from github import Github
import os
import io

# --- GitHub Setup ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
g = Github(GITHUB_TOKEN)
REPO_NAME = "Abdullahshade/repoabood"
FILE_PATH = "chunk_1.csv"
images_folder = "Chunk1"

# --- Load Data from GitHub (No Caching) ---
def load_data():
    try:
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        csv_content = contents.decoded_content
        return pd.read_csv(io.BytesIO(csv_content))
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()

GT_Pneumothorax = load_data()

# --- Session State Setup ---
if "unlabeled_indices" not in st.session_state:
    st.session_state.unlabeled_indices = GT_Pneumothorax.index[GT_Pneumothorax["Label_Flag"] == 0].tolist()
    
if "current_pos" not in st.session_state:
    st.session_state.current_pos = 0 if st.session_state.unlabeled_indices else -1

# --- Reset Button ---
if st.button("⟳ Reset App State"):
    st.session_state.clear()
    st.rerun()

# --- Get Current Image Data ---
def get_current_image():
    if st.session_state.current_pos == -1:
        return None
    
    try:
        idx = st.session_state.unlabeled_indices[st.session_state.current_pos]
        row = GT_Pneumothorax.iloc[idx]
        image_path = os.path.join(images_folder, row["Image_Name"])
        
        if not os.path.exists(image_path):
            st.error(f"Image {row['Image_Name']} not found!")
            return None
            
        return (idx, row, Image.open(image_path))
    except IndexError:
        st.session_state.current_pos = -1
        return None

# --- Main Display Logic ---
current_image = get_current_image()

if not current_image:
    st.warning("No unlabeled images remaining!")
    if st.checkbox("Show all images anyway"):
        st.session_state.current_pos = 0
        st.session_state.unlabeled_indices = GT_Pneumothorax.index.tolist()
        current_image = get_current_image()
    else:
        st.stop()

idx, row, img = current_image
st.image(img, caption=f"Image {idx + 1}/{len(GT_Pneumothorax)}", use_column_width=True)

# --- Grading Form ---
with st.form(key="grading_form"):
    current_type = row.get("Pneumothorax_Type", "Simple")
    current_size = row.get("Pneumothorax_Size", "Small")
    current_side = row.get("Affected_Side", "Right")

    pneumothorax_type = st.selectbox(
        "Pneumothorax Type", ["Simple", "Tension"],
        index=0 if current_type == "Simple" else 1
    )
    pneumothorax_size = st.selectbox(
        "Pneumothorax Size", ["Small", "Large"],
        index=0 if current_size == "Small" else 1
    )
    affected_side = st.selectbox(
        "Affected Side", ["Right", "Left"],
        index=0 if current_side == "Right" else 1
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        form_submit = st.form_submit_button("💾 Save")
    with col2:
        drop_submit = st.form_submit_button("🗑️ Drop")

# --- Save/Drop Handling ---
def update_system():
    try:
        # Update GitHub
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        updated_csv = GT_Pneumothorax.to_csv(index=False).encode("utf-8")
        repo.update_file(contents.path, "Updated labels", updated_csv, contents.sha)
        
        # Update local session state
        new_unlabeled = GT_Pneumothorax.index[GT_Pneumothorax["Label_Flag"] == 0].tolist()
        st.session_state.unlabeled_indices = new_unlabeled
        st.session_state.current_pos = 0 if new_unlabeled else -1
        
        st.success("Changes saved!")
    except Exception as e:
        st.error(f"Save failed: {e}")

if form_submit or drop_submit:
    # Update DataFrame
    GT_Pneumothorax.at[idx, "Pneumothorax_Type"] = pneumothorax_type
    GT_Pneumothorax.at[idx, "Pneumothorax_Size"] = pneumothorax_size
    GT_Pneumothorax.at[idx, "Affected_Side"] = affected_side
    GT_Pneumothorax.at[idx, "Label_Flag"] = 1
    GT_Pneumothorax.at[idx, "Drop"] = "True" if drop_submit else "False"
    
    update_system()
    st.rerun()

# --- Navigation Controls ---
col_prev, col_next = st.columns(2)

with col_prev:
    if st.button("⏮️ Previous"):
        if st.session_state.current_pos > 0:
            st.session_state.current_pos -= 1
            st.rerun()

with col_next:
    if st.button("⏭️ Next"):
        if st.session_state.current_pos < len(st.session_state.unlabeled_indices) - 1:
            st.session_state.current_pos += 1
            st.rerun()

# --- Progress Display ---
if st.session_state.unlabeled_indices:
    progress = (st.session_state.current_pos + 1) / len(st.session_state.unlabeled_indices)
    st.progress(progress)
    st.caption(f"Unlabeled Progress: {st.session_state.current_pos + 1}/{len(st.session_state.unlabeled_indices)}")
