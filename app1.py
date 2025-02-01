import streamlit as st
import pandas as pd
from PIL import Image
from github import Github
import os
import sys

def safe_rerun():
    """Force a rerun of the app."""
    if hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    else:
        sys.exit(0)

# -----------------------------
# Helper function: get the next ungraded index
# -----------------------------
def get_next_index(df, current_index):
    """Advance to the next row that has not been labeled (Label_Flag != 1)."""
    next_index = current_index + 1
    while next_index < len(df) and df.iloc[next_index]["Label_Flag"] == 1:
        next_index += 1
    return next_index

# -----------------------------
# GitHub and file setup
# -----------------------------
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
g = Github(GITHUB_TOKEN)
REPO_NAME = "Abdullahshade/repoabood"  # Replace with your repository name
FILE_PATH = "chunk_1.csv"              # Path to metadata CSV in GitHub
repo = g.get_repo(REPO_NAME)

images_folder = "Chunk1"   # Folder where images are stored
csv_file_path = "chunk_1.csv"  # Local CSV file path

# -----------------------------
# Load metadata from GitHub
# -----------------------------
try:
    contents = repo.get_contents(FILE_PATH)
    with open(csv_file_path, "wb") as f:
        f.write(contents.decoded_content)
    GT_Pneumothorax = pd.read_csv(csv_file_path)
except Exception as e:
    st.error(f"Failed to fetch metadata from GitHub: {e}")
    st.stop()

# -----------------------------
# Streamlit UI setup
# -----------------------------
st.title("Pneumothorax Grading and Image Viewer")

# Initialize session state for the current index
if "current_index" not in st.session_state:
    st.session_state.current_index = 0

# Skip already processed images (where Label_Flag == 1)
while (st.session_state.current_index < len(GT_Pneumothorax) and 
       GT_Pneumothorax.iloc[st.session_state.current_index]["Label_Flag"] == 1):
    st.session_state.current_index += 1

# Check if there are still images left to process
if st.session_state.current_index >= len(GT_Pneumothorax):
    st.success("All images have been labeled! No more images to process.")
    st.stop()

# Get the current row (image and metadata)
row = GT_Pneumothorax.iloc[st.session_state.current_index]

# Build the image path based on Image_Name column
image_path = os.path.join(images_folder, row["Image_Name"])

# Display the image if found
if os.path.exists(image_path):
    img = Image.open(image_path)
    st.image(
        img,
        caption=f"Image index: {row['Index']} | Image Name: {row['Image_Name']}",
        use_container_width=True
    )
else:
    st.error(f"Image {row['Image_Name']} not found in {images_folder}.")
    st.stop()

# -----------------------------
# Form for grading the image
# -----------------------------
with st.form(key="grading_form"):
    pneumothorax_type = st.selectbox("Pneumothorax Type", ["Simple", "Tension"])
    pneumothorax_size = st.selectbox("Pneumothorax Size", ["Small", "Large"])
    affected_side = st.selectbox("Affected Side", ["Right", "Left"])
    submit_button = st.form_submit_button("Save Changes")

# A separate button for dropping the image
drop_button = st.button("Drop")

# -----------------------------
# Handle Drop functionality
# -----------------------------
if drop_button:
    # Mark the current image as dropped
    GT_Pneumothorax.at[st.session_state.current_index, "Label_Flag"] = 1
    GT_Pneumothorax.at[st.session_state.current_index, "Drop"] = "True"
    try:
        # Save the updated CSV locally
        GT_Pneumothorax.to_csv(csv_file_path, index=False)
        updated_content = GT_Pneumothorax.to_csv(index=False)
        repo.update_file(
            path=contents.path,
            message="Mark image as dropped",
            content=updated_content,
            sha=contents.sha
        )
        st.success(f"Image {row['Image_Name']} marked as dropped and changes pushed to GitHub!")
        
        # Advance to the next ungraded image and refresh the page
        st.session_state.current_index = get_next_index(GT_Pneumothorax, st.session_state.current_index)
        safe_rerun()
    except Exception as e:
        st.error(f"Failed to save changes or push to GitHub: {e}")

# -----------------------------
# Handle form submission (grading changes)
# -----------------------------
elif submit_button:
    GT_Pneumothorax.at[st.session_state.current_index, "Pneumothorax_Type"] = pneumothorax_type
    GT_Pneumothorax.at[st.session_state.current_index, "Pneumothorax_Size"] = pneumothorax_size
    GT_Pneumothorax.at[st.session_state.current_index, "Affected_Side"] = affected_side
    GT_Pneumothorax.at[st.session_state.current_index, "Label_Flag"] = 1  # Mark as labeled
    GT_Pneumothorax.at[st.session_state.current_index, "Drop"] = "False"
    try:
        # Save changes locally and push the updated CSV to GitHub
        GT_Pneumothorax.to_csv(csv_file_path, index=False)
        updated_content = GT_Pneumothorax.to_csv(index=False)
        repo.update_file(
            path=contents.path,
            message="Update metadata with pneumothorax grading",
            content=updated_content,
            sha=contents.sha
        )
        st.success(f"Changes saved for Image {row['Image_Name']} and pushed to GitHub!")
        
        # Advance to the next ungraded image and refresh the page
        st.session_state.current_index = get_next_index(GT_Pneumothorax, st.session_state.current_index)
        safe_rerun()
    except Exception as e:
        st.error(f"Failed to save changes or push to GitHub: {e}")

# -----------------------------
# Navigation buttons (Previous / Next)
# -----------------------------
col1, col2 = st.columns(2)
if col1.button("Previous") and st.session_state.current_index > 0:
    st.session_state.current_index -= 1
    safe_rerun()
if col2.button("Next") and st.session_state.current_index < len(GT_Pneumothorax) - 1:
    st.session_state.current_index += 1
    safe_rerun()
