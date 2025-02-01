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

# --- Load Data from GitHub ---
@st.cache_data
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
if "current_index" not in st.session_state:
    st.session_state.current_index = 0

# --- Reset Button ---
if st.button("⟳ Reset App State"):
    st.session_state.clear()
    st.rerun()

# --- Find Next Unlabeled Image ---
def find_next_unlabeled(start_index):
    index = start_index
    while index < len(GT_Pneumothorax):
        if GT_Pneumothorax.iloc[index].get("Label_Flag", 0) == 0:
            return index
        index += 1
    return index

# --- Find Previous Unlabeled Image ---
def find_previous_unlabeled(start_index):
    index = start_index
    while index >= 0:
        if GT_Pneumothorax.iloc[index].get("Label_Flag", 0) == 0:
            return index
        index -= 1
    return index

# --- Initial Index Setup ---
if st.session_state.current_index >= len(GT_Pneumothorax) or \
   GT_Pneumothorax.iloc[st.session_state.current_index].get("Label_Flag", 0) == 1:
    st.session_state.current_index = find_next_unlabeled(0)

# --- Check if All Labeled ---
if GT_Pneumothorax["Label_Flag"].sum() == len(GT_Pneumothorax):
    st.warning("All images are labeled. Check the CSV or toggle below to review.")
    if st.checkbox("Show labeled images anyway"):
        st.session_state.current_index = 0
    else:
        st.stop()

# --- Get Current Image Data ---
row = GT_Pneumothorax.iloc[st.session_state.current_index]
image_path = os.path.join(images_folder, row["Image_Name"])

# --- Display Image ---
if not os.path.exists(image_path):
    st.error(f"Image {row['Image_Name']} not found!")
    st.stop()

img = Image.open(image_path)
st.image(img, caption=f"Image {st.session_state.current_index + 1}/{len(GT_Pneumothorax)}", use_column_width=True)

# --- Grading Form with Pre-Populated Values ---
with st.form(key="grading_form"):
    # Get current values or use defaults
    current_type = row["Pneumothorax_Type"] if pd.notna(row["Pneumothorax_Type"]) else "Simple"
    current_size = row["Pneumothorax_Size"] if pd.notna(row["Pneumothorax_Size"]) else "Small"
    current_side = row["Affected_Side"] if pd.notna(row["Affected_Side"]) else "Right"

    # Form elements
    pneumothorax_type = st.selectbox(
        "Pneumothorax Type",
        ["Simple", "Tension"],
        index=0 if current_type == "Simple" else 1
    )
    pneumothorax_size = st.selectbox(
        "Pneumothorax Size",
        ["Small", "Large"],
        index=0 if current_size == "Small" else 1
    )
    affected_side = st.selectbox(
        "Affected Side",
        ["Right", "Left"],
        index=0 if current_side == "Right" else 1
    )

    # Form buttons
    col1, col2 = st.columns([1, 3])
    with col1:
        form_submit = st.form_submit_button("💾 Save")
    with col2:
        drop_submit = st.form_submit_button("🗑️ Drop")

# --- Save/Drop Handling ---
def update_github():
    try:
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        updated_csv = GT_Pneumothorax.to_csv(index=False).encode("utf-8")
        repo.update_file(contents.path, "Updated labels", updated_csv, contents.sha)
        st.success("Changes saved to GitHub!")
    except Exception as e:
        st.error(f"GitHub update failed: {e}")

if form_submit or drop_submit:
    # Update DataFrame
    GT_Pneumothorax.at[st.session_state.current_index, "Pneumothorax_Type"] = pneumothorax_type
    GT_Pneumothorax.at[st.session_state.current_index, "Pneumothorax_Size"] = pneumothorax_size
    GT_Pneumothorax.at[st.session_state.current_index, "Affected_Side"] = affected_side
    GT_Pneumothorax.at[st.session_state.current_index, "Label_Flag"] = 1
    GT_Pneumothorax.at[st.session_state.current_index, "Drop"] = "True" if drop_submit else "False"
    
    # Update GitHub and move to next image
    update_github()
    st.session_state.current_index = find_next_unlabeled(st.session_state.current_index + 1)
    st.rerun()

# --- Navigation Controls ---
col_prev, col_next = st.columns(2)
with col_prev:
    if st.button("⏮️ Previous"):
        new_index = find_previous_unlabeled(st.session_state.current_index - 1)
        if new_index >= 0:
            st.session_state.current_index = new_index
            st.rerun()
with col_next:
    if st.button("⏭️ Next"):
        new_index = find_next_unlabeled(st.session_state.current_index + 1)
        if new_index < len(GT_Pneumothorax):
            st.session_state.current_index = new_index
            st.rerun()

# --- Progress Display ---
progress = st.session_state.current_index / len(GT_Pneumothorax)
st.progress(progress)
st.caption(f"Progress: {st.session_state.current_index + 1}/{len(GT_Pneumothorax)} images")
