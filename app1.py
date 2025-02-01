import streamlit as st
import pandas as pd
from PIL import Image
from github import Github
import os

# Load GitHub token from Streamlit secrets
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
g = Github(GITHUB_TOKEN)

# Define repository and file paths
REPO_NAME = "Abdullahshade/repoabood"
FILE_PATH = "chunk_1.csv"
repo = g.get_repo(REPO_NAME)

# Define paths
images_folder = "Chunk1"
csv_file_path = "chunk_1.csv"

# Function to reload metadata from GitHub
def reload_metadata():
    try:
        contents = repo.get_contents(FILE_PATH)
        with open(csv_file_path, "wb") as f:
            f.write(contents.decoded_content)
        return pd.read_csv(csv_file_path)
    except Exception as e:
        st.error(f"Failed to reload metadata: {e}")
        st.stop()

# Load initial metadata
GT_Pneumothorax = reload_metadata()

# App title
st.title("Pneumothorax Grading and Image !#Viewer")

# Initialize session state for the current index
if "current_index" not in st.session_state:
    st.session_state.current_index = 0

# Function to skip labeled/dropped images
def update_current_index():
    while st.session_state.current_index < len(GT_Pneumothorax):
        row = GT_Pneumothorax.iloc[st.session_state.current_index]
        if row["Label_Flag"] == 1:
            st.session_state.current_index += 1
        else:
            break

update_current_index()

# Check if all images are labeled
if st.session_state.current_index >= len(GT_Pneumothorax):
    st.success("All images have been labeled! No more images to process.")
    st.stop()

# Get current row and image
row = GT_Pneumothorax.iloc[st.session_state.current_index]
image_path = os.path.join(images_folder, row["Image_Name"])

if not os.path.exists(image_path):
    st.error(f"Image {row['Image_Name']} not found in {images_folder}.")
    st.stop()

img = Image.open(image_path)
st.image(img, caption=f"Image index: {row['Index']} | Name: {row['Image_Name']}", use_container_width=True)

# Grading form
with st.form(key="grading_form"):
    pneumothorax_type = st.selectbox("Pneumothorax Type", ["Simple", "Tension"], index=0)
    pneumothorax_size = st.selectbox("Pneumothorax Size", ["Small", "Large"], index=0)
    affected_side = st.selectbox("Affected Side", ["Right", "Left"], index=0)
    form_submit = st.form_submit_button("Save Changes")

# Drop button
drop_button = st.button("Drop")

# Handle drop action
if drop_button:
    GT_Pneumothorax.at[st.session_state.current_index, "Label_Flag"] = 1
    GT_Pneumothorax.at[st.session_state.current_index, "Drop"] = "True"
    try:
        GT_Pneumothorax.to_csv(csv_file_path, index=False)
        updated_content = GT_Pneumothorax.to_csv(index=False)
        repo.update_file(contents.path, "Mark image as dropped", updated_content, contents.sha)
        st.success("Image dropped and changes pushed to GitHub!")
        GT_Pneumothorax = reload_metadata()  # Reload DataFrame
        update_current_index()  # Reset index
    except Exception as e:
        st.error(f"Error: {e}")

# Handle form submission
elif form_submit:
    GT_Pneumothorax.at[st.session_state.current_index, "Pneumothorax_Type"] = pneumothorax_type
    GT_Pneumothorax.at[st.session_state.current_index, "Pneumothorax_Size"] = pneumothorax_size
    GT_Pneumothorax.at[st.session_state.current_index, "Affected_Side"] = affected_side
    GT_Pneumothorax.at[st.session_state.current_index, "Label_Flag"] = 1
    GT_Pneumothorax.at[st.session_state.current_index, "Drop"] = "False"
    try:
        GT_Pneumothorax.to_csv(csv_file_path, index=False)
        updated_content = GT_Pneumothorax.to_csv(index=False)
        repo.update_file(contents.path, "Update metadata", updated_content, contents.sha)
        st.success("Changes saved and pushed to GitHub!")
        GT_Pneumothorax = reload_metadata()  # Reload DataFrame
        update_current_index()  # Reset index
    except Exception as e:
        st.error(f"Error: {e}")

# Navigation buttons
col1, col2 = st.columns(2)
if col1.button("Previous") and st.session_state.current_index > 0:
    st.session_state.current_index -= 1
    update_current_index()

if col2.button("Next") and st.session_state.current_index < len(GT_Pneumothorax) - 1:
    st.session_state.current_index += 1
    update_current_index()
