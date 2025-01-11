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
FILE_PATH = "chunk_1.csv"  # Path to metadata CSV in your GitHub repo
repo = g.get_repo(REPO_NAME)

# App title
st.title("Pneumothorax Grading and Image Viewer")

# Define local paths
images_folder = "Chunk1"
csv_file_path = "chunk_1.csv"

# Fetch and load the CSV metadata from GitHub
try:
    # Get the latest CSV file from the GitHub repository
    contents = repo.get_contents(FILE_PATH)
    with open(csv_file_path, "wb") as f:
        f.write(contents.decoded_content)
    GT_Pneumothorax = pd.read_csv(csv_file_path)
except Exception as e:
    st.error(f"Failed to fetch metadata from GitHub: {e}")
    st.stop()

# Initialize session state for the current index
if "current_index" not in st.session_state:
    st.session_state.current_index = 0

# Function to save updates to GitHub
def save_to_github(updated_df, commit_message):
    try:
        # Convert DataFrame to CSV string
        updated_content = updated_df.to_csv(index=False)
        # Push updated file to GitHub
        repo.update_file(
            path=contents.path,
            message=commit_message,
            content=updated_content,
            sha=contents.sha
        )
        st.success("Changes successfully saved and pushed to GitHub!")
    except Exception as e:
        st.error(f"Failed to push changes to GitHub: {e}")

# Skip labeled images automatically
while st.session_state.current_index < len(GT_Pneumothorax):
    row = GT_Pneumothorax.iloc[st.session_state.current_index]
    if row["Label_Flag"] == 1:  # Skip already labeled images
        st.session_state.current_index += 1
    else:
        break

# Ensure there are still images left to process
if st.session_state.current_index >= len(GT_Pneumothorax):
    st.success("All images have been labeled! No more images to process.")
    st.stop()

# Get the current row
row = GT_Pneumothorax.iloc[st.session_state.current_index]
image_path = os.path.join(images_folder, row["Image_Name"])

# Display the current image
if os.path.exists(image_path):
    img = Image.open(image_path)
    st.image(img, caption=f"Image index: {row['Index']} | Image Name: {row['Image_Name']}", use_column_width=True)
else:
    st.error(f"Image {row['Image_Name']} not found in {images_folder}.")
    st.stop()

# User input fields
drop_checkbox = st.checkbox("Drop this image", value=(row.get("Drop") == "True"))
pneumothorax_type = st.selectbox("Pneumothorax Type", ["Simple", "Tension"], index=0 if pd.isna(row.get("Pneumothorax_Type")) else ["Simple", "Tension"].index(row["Pneumothorax_Type"]))
pneumothorax_size = st.selectbox("Pneumothorax Size", ["Small", "Large"], index=0 if pd.isna(row.get("Pneumothorax_Size")) else ["Small", "Large"].index(row["Pneumothorax_Size"]))
affected_side = st.selectbox("Affected Side", ["Right", "Left"], index=0 if pd.isna(row.get("Affected_Side")) else ["Right", "Left"].index(row["Affected_Side"]))

# Save changes button
if st.button("Save Changes"):
    GT_Pneumothorax.at[st.session_state.current_index, "Pneumothorax_Type"] = pneumothorax_type
    GT_Pneumothorax.at[st.session_state.current_index, "Pneumothorax_Size"] = pneumothorax_size
    GT_Pneumothorax.at[st.session_state.current_index, "Affected_Side"] = affected_side
    GT_Pneumothorax.at[st.session_state.current_index, "Label_Flag"] = 1
    GT_Pneumothorax.at[st.session_state.current_index, "Drop"] = str(drop_checkbox)
    try:
        # Save changes locally
        GT_Pneumothorax.to_csv(csv_file_path, index=False)
        # Push changes to GitHub
        save_to_github(GT_Pneumothorax, "Updated metadata with user annotations")
    except Exception as e:
        st.error(f"Failed to save changes: {e}")

# Navigation buttons
col1, col2 = st.columns(2)
if col1.button("Previous") and st.session_state.current_index > 0:
    st.session_state.current_index -= 1
if col2.button("Next") and st.session_state.current_index < len(GT_Pneumothorax) - 1:
    st.session_state.current_index += 1
