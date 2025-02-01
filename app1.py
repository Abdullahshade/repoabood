import streamlit as st
import pandas as pd
from PIL import Image
from github import Github
import os

# -----------------------------------------------------------------
# 1. Fallback function for rerun
# -----------------------------------------------------------------
def safe_rerun():
    """Try st.experimental_rerun(), fallback if Streamlit < 1.10."""
    try:
        st.experimental_rerun()
    except AttributeError:
        st.warning("Please manually refresh or navigate. "
                   "Upgrade Streamlit to >= 1.10 to enable automatic rerun.")
        st.stop()

# -----------------------------------------------------------------
# 2. Setup: GitHub, CSV, etc.
# -----------------------------------------------------------------
# Load GitHub token from Streamlit secrets
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
g = Github(GITHUB_TOKEN)

REPO_NAME = "Abdullahshade/repoabood"  # Replace with your GitHub repo
FILE_PATH = "chunk_1.csv"             # Path to the CSV in your repo

# Local paths
csv_file_path = "chunk_1.csv"         # Local file name for CSV
images_folder = "Chunk1"              # Folder containing images

repo = g.get_repo(REPO_NAME)

# -----------------------------------------------------------------
# 3. Fetch CSV from GitHub
# -----------------------------------------------------------------
try:
    contents = repo.get_contents(FILE_PATH)
    with open(csv_file_path, "wb") as f:
        f.write(contents.decoded_content)

    GT_Pneumothorax = pd.read_csv(csv_file_path)
except Exception as e:
    st.error(f"Failed to fetch metadata from GitHub: {e}")
    st.stop()

# -----------------------------------------------------------------
# 4. Streamlit UI
# -----------------------------------------------------------------
st.title("Pneumothorax Grading and Image Viewer")

if "current_index" not in st.session_state:
    st.session_state.current_index = 0

# Skip labeled/dropped rows
while st.session_state.current_index < len(GT_Pneumothorax):
    tmp_row = GT_Pneumothorax.iloc[st.session_state.current_index]
    if tmp_row.get("Label_Flag", 0) == 1:
        st.session_state.current_index += 1
    else:
        break

if st.session_state.current_index >= len(GT_Pneumothorax):
    st.success("All images are labeled! No more to process.")
    st.stop()

row = GT_Pneumothorax.iloc[st.session_state.current_index]
current_unique_id = row["Index"]  # Unique identifier from CSV row

image_path = os.path.join(images_folder, row["Image_Name"])
if os.path.exists(image_path):
    img = Image.open(image_path)
    st.image(img, caption=f"Index={row['Index']} | Name={row['Image_Name']}")
else:
    st.error(f"Image {row['Image_Name']} not found in {images_folder}.")
    st.stop()

# -----------------------------------------------------------------
# 5. Helper: Push changes to GitHub
# -----------------------------------------------------------------
def push_changes_to_github(df, message):
    global contents

    # Save local CSV
    df.to_csv(csv_file_path, index=False)
    updated_content = df.to_csv(index=False)

    # Update on GitHub
    update_response = repo.update_file(
        path=contents.path,
        message=message,
        content=updated_content,
        sha=contents.sha
    )
    st.success(message)

    # Re-fetch to get new sha
    contents = repo.get_contents(FILE_PATH)

# -----------------------------------------------------------------
# 6. Form for grading
# -----------------------------------------------------------------
with st.form(key="grading_form"):
    pneumothorax_type = st.selectbox("Pneumothorax Type", ["Simple", "Tension"], index=0)
    pneumothorax_size = st.selectbox("Pneumothorax Size", ["Small", "Large"], index=0)
    affected_side = st.selectbox("Affected Side", ["Right", "Left"], index=0)

    form_submit = st.form_submit_button("Save Changes")

drop_button = st.button("Drop")

# -----------------------------------------------------------------
# 7. Handle "Drop"
# -----------------------------------------------------------------
if drop_button:
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Label_Flag"] = 1
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Drop"] = "True"

    try:
        push_changes_to_github(
            GT_Pneumothorax,
            message=f"Drop image {row['Image_Name']} (Index={current_unique_id})"
        )
        st.session_state.current_index += 1
        safe_rerun()  # Try to rerun
    except Exception as e:
        st.error(f"Failed to save or push to GitHub: {e}")

# -----------------------------------------------------------------
# 8. Handle "Save Changes"
# -----------------------------------------------------------------
elif form_submit:
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Pneumothorax_Type"] = pneumothorax_type
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Pneumothorax_Size"] = pneumothorax_size
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Affected_Side"] = affected_side
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Label_Flag"] = 1
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Drop"] = "False"

    try:
        push_changes_to_github(
            GT_Pneumothorax,
            message=f"Update metadata for {row['Image_Name']} (Index={current_unique_id})"
        )
        st.session_state.current_index += 1
        safe_rerun()  # Try to rerun
    except Exception as e:
        st.error(f"Failed to save or push to GitHub: {e}")

# -----------------------------------------------------------------
# 9. Navigation
# -----------------------------------------------------------------
col1, col2 = st.columns(2)

if col1.button("Previous") and st.session_state.current_index > 0:
    st.session_state.current_index -= 1
    safe_rerun()

if col2.button("Next") and st.session_state.current_index < len(GT_Pneumothorax) - 1:
    st.session_state.current_index += 1
    safe_rerun()
