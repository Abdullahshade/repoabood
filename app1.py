import streamlit as st
import pandas as pd
from PIL import Image
from github import Github
import os

# Load GitHub token from Streamlit secrets
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
g = Github(GITHUB_TOKEN)

# Define repository and file paths
REPO_NAME = "Abdullahshade/repoabood"  # Replace with your GitHub repository name
FILE_PATH = "chunk_1.csv"             # Path to metadata CSV in your GitHub repo
repo = g.get_repo(REPO_NAME)

# Define local paths (images folder, local CSV, etc.)
images_folder = "Chunk1"         # Path to images folder
csv_file_path = "chunk_1.csv"    # Local CSV path

# Fetch the latest file from GitHub and load into a DataFrame
try:
    contents = repo.get_contents(FILE_PATH)
    with open(csv_file_path, "wb") as f:
        f.write(contents.decoded_content)
    GT_Pneumothorax = pd.read_csv(csv_file_path)
except Exception as e:
    st.error(f"Failed to fetch metadata from GitHub: {e}")
    st.stop()

st.title("Pneumothorax !!!Grading and Image Viewer")

# Initialize or restore the current index in session state
if "current_index" not in st.session_state:
    st.session_state.current_index = 0

# Skip any rows that are already labeled or dropped until we find an unlabeled row
while st.session_state.current_index < len(GT_Pneumothorax):
    tmp_row = GT_Pneumothorax.iloc[st.session_state.current_index]
    if tmp_row["Label_Flag"] == 1:
        st.session_state.current_index += 1
    else:
        break

# If we've gone past all rows, we're done
if st.session_state.current_index >= len(GT_Pneumothorax):
    st.success("All images have been labeled! No more images to process.")
    st.stop()

# Get row by its DataFrame position
row = GT_Pneumothorax.iloc[st.session_state.current_index]
# Store the unique ID from the CSV row. 
# For example, if your CSV has a column literally called "Index"
current_unique_id = row["Index"]

# Construct the image path
image_path = os.path.join(images_folder, row["Image_Name"])
if os.path.exists(image_path):
    img = Image.open(image_path)
    st.image(
        img,
        caption=f"Image index (CSV 'Index' column): {row['Index']} | Image Name: {row['Image_Name']}",
        use_container_width=True
    )
else:
    st.error(f"Image {row['Image_Name']} not found in {images_folder}.")
    st.stop()

# --- Form for grading the image ---
with st.form(key="grading_form"):
    pneumothorax_type = st.selectbox("Pneumothorax Type", ["Simple", "Tension"], index=0)
    pneumothorax_size = st.selectbox("Pneumothorax Size", ["Small", "Large"], index=0)
    affected_side = st.selectbox("Affected Side", ["Right", "Left"], index=0)
    
    form_submit = st.form_submit_button("Save Changes")

# Drop button outside the form
drop_button = st.button("Drop")

def push_changes_to_github(df, message):
    """
    Helper function to push DataFrame changes to GitHub,
    updating the local `contents` with the new sha.
    """
    global contents

    # Save updated CSV locally
    df.to_csv(csv_file_path, index=False)

    # Prepare content for GitHub
    updated_content = df.to_csv(index=False)

    # Update file on GitHub
    update_response = repo.update_file(
        path=contents.path,
        message=message,
        content=updated_content,
        sha=contents.sha
    )
    st.success(message)

    # IMPORTANT: update contents.sha so that subsequent updates
    # reference the latest commit.
    contents.sha = update_response["content"].sha


# --- Handle "Drop" functionality ---
if drop_button:
    # Use .loc with the unique ID to ensure the correct row is updated
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Label_Flag"] = 1
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Drop"] = "True"
    try:
        push_changes_to_github(GT_Pneumothorax, f"Mark image {row['Image_Name']} as dropped")
        # Move on to next image (optional)
        st.session_state.current_index += 1
        st.experimental_rerun()
    except Exception as e:
        st.error(f"Failed to save changes or push to GitHub: {e}")

# --- Handle "Save Changes" (grading) in the form ---
elif form_submit:
    # Update the correct row, using .loc plus the unique ID
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Pneumothorax_Type"] = pneumothorax_type
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Pneumothorax_Size"] = pneumothorax_size
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Affected_Side"] = affected_side
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Label_Flag"] = 1
    GT_Pneumothorax.loc[GT_Pneumothorax["Index"] == current_unique_id, "Drop"] = "False"

    try:
        push_changes_to_github(GT_Pneumothorax, f"Update metadata for image {row['Image_Name']}")
        # Move on to next image (optional)
        st.session_state.current_index += 1
        st.experimental_rerun()
    except Exception as e:
        st.error(f"Failed to save changes or push to GitHub: {e}")

# --- Navigation buttons (Previous / Next) ---
col1, col2 = st.columns(2)
if col1.button("Previous") and st.session_state.current_index > 0:
    st.session_state.current_index -= 1
    st.experimental_rerun()
if col2.button("Next") and st.session_state.current_index < len(GT_Pneumothorax) - 1:
    st.session_state.current_index += 1
    st.experimental_rerun()
