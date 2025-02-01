import streamlit as st
import pandas as pd
from PIL import Image
from github import Github
import os

# ------------------------------------------------------------------------------
# 1. GitHub and CSV Setup
# ------------------------------------------------------------------------------
# Load GitHub token from Streamlit secrets
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
g = Github(GITHUB_TOKEN)

# Define repository name and the path to the CSV file in GitHub
REPO_NAME = "Abdullahshade/repoabood"  # <<-- Your GitHub repo
FILE_PATH = "chunk_1.csv"             # <<-- Path to the CSV in your repo

# Local paths
csv_file_path = "chunk_1.csv"         # <<-- Where you'll store it locally
images_folder = "Chunk1"              # <<-- Folder where images are stored

# Get reference to the repo
repo = g.get_repo(REPO_NAME)

# ------------------------------------------------------------------------------
# 2. Fetch CSV from GitHub
# ------------------------------------------------------------------------------
try:
    # Initial fetch of the CSV content from GitHub
    contents = repo.get_contents(FILE_PATH)
    with open(csv_file_path, "wb") as f:
        f.write(contents.decoded_content)

    # Read into a DataFrame
    GT_Pneumothorax = pd.read_csv(csv_file_path)
except Exception as e:
    st.error(f"Failed to fetch metadata from GitHub: {e}")
    st.stop()

# ------------------------------------------------------------------------------
# 3. Streamlit UI: Title, Session State
# ------------------------------------------------------------------------------
st.title("Pneumothorax Grading and Image Viewer")

if "current_index" not in st.session_state:
    st.session_state.current_index = 0

# ------------------------------------------------------------------------------
# 4. Skip over labeled or dropped rows automatically
# ------------------------------------------------------------------------------
while st.session_state.current_index < len(GT_Pneumothorax):
    tmp_row = GT_Pneumothorax.iloc[st.session_state.current_index]
    # We assume "Label_Flag == 1" means it's already labeled or dropped
    if tmp_row.get("Label_Flag", 0) == 1:
        st.session_state.current_index += 1
    else:
        break

# If we've gone past all rows, we're done
if st.session_state.current_index >= len(GT_Pneumothorax):
    st.success("All images have been labeled! No more images to process.")
    st.stop()

# ------------------------------------------------------------------------------
# 5. Select the current row and display its image
# ------------------------------------------------------------------------------
row = GT_Pneumothorax.iloc[st.session_state.current_index]

# We'll store a unique ID from the CSV (assuming "Index" is unique)
current_unique_id = row["Index"]

# Check if the image file exists and display it
image_path = os.path.join(images_folder, row["Image_Name"])
if os.path.exists(image_path):
    img = Image.open(image_path)
    st.image(
        img,
        caption=f"CSV 'Index' = {row['Index']} | Image Name: {row['Image_Name']}",
        use_container_width=True
    )
else:
    st.error(f"Image {row['Image_Name']} not found in {images_folder}.")
    st.stop()

# ------------------------------------------------------------------------------
# 6. Helper function to push changes back to GitHub
# ------------------------------------------------------------------------------
def push_changes_to_github(df: pd.DataFrame, message: str):
    """
    Saves the DataFrame locally, updates the file in GitHub,
    and re-fetches the contents so we get the new sha.
    """
    global contents

    # 1. Save CSV locally
    df.to_csv(csv_file_path, index=False)

    # 2. Convert DF to CSV string
    updated_content = df.to_csv(index=False)

    # 3. Update file on GitHub using the *current* contents.sha
    update_response = repo.update_file(
        path=contents.path,
        message=message,
        content=updated_content,
        sha=contents.sha
    )

    # 4. Show success message in Streamlit
    st.success(message)

    # 5. Re-fetch contents from GitHub -> new sha
    contents = repo.get_contents(FILE_PATH)

# ------------------------------------------------------------------------------
# 7. Form for grading & "Drop" button
# ------------------------------------------------------------------------------
with st.form(key="grading_form"):
    pneumothorax_type = st.selectbox("Pneumothorax Type", ["Simple", "Tension"], index=0)
    pneumothorax_size = st.selectbox("Pneumothorax Size", ["Small", "Large"], index=0)
    affected_side = st.selectbox("Affected Side", ["Right", "Left"], index=0)

    # "Save Changes" inside the form
    form_submit = st.form_submit_button("Save Changes")

# "Drop" button is outside the form
drop_button = st.button("Drop")

# ------------------------------------------------------------------------------
# 8. Handle "Drop" functionality
# ------------------------------------------------------------------------------
if drop_button:
    # Locate the row by the unique ID and mark it dropped
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Label_Flag"] = 1
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Drop"] = "True"

    try:
        push_changes_to_github(
            GT_Pneumothorax,
            message=f"Mark image {row['Image_Name']} as dropped (Index={current_unique_id})"
        )
        # Move on to the next image
        st.session_state.current_index += 1
        st.experimental_rerun()
    except Exception as e:
        st.error(f"Failed to save changes or push to GitHub: {e}")

# ------------------------------------------------------------------------------
# 9. Handle "Save Changes" for grading
# ------------------------------------------------------------------------------
elif form_submit:
    # Update the row (loc, not iloc) so we get the correct row by unique ID
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Pneumothorax_Type"] = pneumothorax_type
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Pneumothorax_Size"] = pneumothorax_size
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Affected_Side"] = affected_side

    # Mark as labeled/not dropped
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Label_Flag"] = 1
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Drop"] = "False"

    try:
        push_changes_to_github(
            GT_Pneumothorax,
            message=f"Update metadata for image {row['Image_Name']} (Index={current_unique_id})"
        )
        # Move on to the next image
        st.session_state.current_index += 1
        st.experimental_rerun()
    except Exception as e:
        st.error(f"Failed to save changes or push to GitHub: {e}")

# ------------------------------------------------------------------------------
# 10. Navigation Buttons (Previous / Next)
# ------------------------------------------------------------------------------
col1, col2 = st.columns(2)

if col1.button("Previous") and st.session_state.current_index > 0:
    st.session_state.current_index -= 1
    st.experimental_rerun()

if col2.button("Next") and st.session_state.current_index < len(GT_Pneumothorax) - 1:
    st.session_state.current_index += 1
    st.experimental_rerun()
