# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license

import io
from typing import Any

import os
import gdown

import cv2
import numpy as np
import streamlit as st

from ultralytics import YOLO
from ultralytics.utils import LOGGER
from ultralytics.utils.checks import check_requirements
from ultralytics.utils.downloads import GITHUB_ASSETS_STEMS


# Define Google Drive file IDs
GDRIVE_MODELS = {
    "YOLO11m_baseline": "1RYJiKwAV2Ueg05_W9U20Y_h0D5SYDFpC",
    "YOLO11m_CA": "1-vh_zLz9OMVCO_6CueKx_MSVVJrCrNhF", 
    "YOLO11m_ECA": "1ZdrB2IcubfM6uJsio4dEOBEcKzlae6-S",
    "YOLO11m_CBAM": "1jKIStEJRGLGhvEPtAx3tRf8O4VLLwwdB",
}


def download_from_gdrive(file_id, model_name):
    """Downloads a YOLO model from Google Drive using wget with confirmation handling."""
    model_path = f"models/{model_name}.pt"
    
    if not os.path.exists(model_path):  # Only download if missing
        os.makedirs("models", exist_ok=True)  # Ensure folder exists

        print(f"📥 Downloading {model_name}.pt ...")
        
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        command = f"wget --no-check-certificate -O {model_path} '{url}'"
        
        try:
            os.system(command)
            
            # Validate file size (to check if download was successful)
            if os.path.exists(model_path) and os.path.getsize(model_path) > 10_000:
                print(f"✅ Successfully downloaded {model_name}.pt ({os.path.getsize(model_path) / (1024 * 1024):.2f} MB).")
            else:
                print(f"❌ Error: {model_name}.pt download failed or incomplete. Try manual download.")
                os.remove(model_path)  # Remove corrupted file
        except Exception as e:
            print(f"❌ Download error: {e}")
    else:
        print(f"✅ {model_name}.pt already exists. Skipping download.")


class Inference:
    """
    A class to perform object detection, image classification, image segmentation and pose estimation inference using
    Streamlit and Ultralytics YOLO models. It provides the functionalities such as loading models, configuring settings,
    uploading video files, and performing real-time inference.

    Attributes:
        st (module): Streamlit module for UI creation.
        temp_dict (dict): Temporary dictionary to store the model path.
        model_path (str): Path to the loaded model.
        model (YOLO): The YOLO model instance.
        source (str): Selected video source.
        enable_trk (str): Enable tracking option.
        conf (float): Confidence threshold.
        iou (float): IoU threshold for non-max suppression.
        vid_file_name (str): Name of the uploaded video file.
        selected_ind (list): List of selected class indices.

    Methods:
        web_ui: Sets up the Streamlit web interface with custom HTML elements.
        sidebar: Configures the Streamlit sidebar for model and inference settings.
        source_upload: Handles video file uploads through the Streamlit interface.
        configure: Configures the model and loads selected classes for inference.
        inference: Performs real-time object detection inference.

    Examples:
        >>> inf = solutions.Inference(model="path/to/model.pt")  # Model is not necessary argument.
        >>> inf.inference()
    """

    def __init__(self, **kwargs: Any):
        """
        Initializes the Inference class, checking Streamlit requirements and setting up the model path.

        Args:
            **kwargs (Any): Additional keyword arguments for model configuration.
        """
        check_requirements("streamlit>=1.29.0")  # scope imports for faster ultralytics package load speeds
        import streamlit as st

        self.st = st  # Reference to the Streamlit class instance
        self.source = None  # Placeholder for video or webcam source details
        self.enable_trk = False  # Flag to toggle object tracking
        self.conf = 0.25  # Confidence threshold for detection
        self.iou = 0.45  # Intersection-over-Union (IoU) threshold for non-maximum suppression
        self.org_frame = None  # Container for the original frame to be displayed
        self.ann_frame = None  # Container for the annotated frame to be displayed
        self.vid_file_name = None  # Holds the name of the video file
        self.selected_ind = []  # List of selected classes for detection or tracking
        self.model = None  # Container for the loaded model instance

        self.temp_dict = {"model": None, **kwargs}
        self.model_path = None  # Store model file name with path
        if self.temp_dict["model"] is not None:
            self.model_path = self.temp_dict["model"]

        LOGGER.info(f"Ultralytics Solutions: ✅ {self.temp_dict}")

    def web_ui(self):
        """Sets up the Streamlit web interface with custom HTML elements."""
        menu_style_cfg = """<style>MainMenu {visibility: hidden;}</style>"""  # Hide main menu style

        # Main title of streamlit application
        main_title_cfg = """<div><h1 style="color:#042AFF; text-align:center; font-size:40px; margin-top:-50px;
        font-family: 'Archivo', sans-serif; margin-bottom:20px;">Ultralytics YOLO Streamlit Application</h1></div>"""

        # Subtitle of streamlit application
        sub_title_cfg = """<div><h4 style="color:#042AFF; text-align:center; font-family: 'Archivo', sans-serif; 
        margin-top:-15px; margin-bottom:50px;">Experience real-time object detection with the power 
        of Ultralytics YOLO! 🚀</h4></div>"""

        # Set html page configuration and append custom HTML
        self.st.set_page_config(page_title="Ultralytics Streamlit App", layout="wide")
        self.st.markdown(menu_style_cfg, unsafe_allow_html=True)
        self.st.markdown(main_title_cfg, unsafe_allow_html=True)
        self.st.markdown(sub_title_cfg, unsafe_allow_html=True)

    def sidebar(self):
        """Configures the Streamlit sidebar for model and inference settings."""
        with self.st.sidebar:  # Add Ultralytics LOGO
            logo = "https://raw.githubusercontent.com/ultralytics/assets/main/logo/Ultralytics_Logotype_Original.svg"
            self.st.image(logo, width=250)
    
        self.st.sidebar.title("User Configuration")  # Sidebar Title
    
        # ✅ Add "image" option in source selection
        self.source = self.st.sidebar.selectbox(
            "Select Source",
            ("webcam", "video", "image"),  # Added "image"
        )
    
        self.enable_trk = self.st.sidebar.radio("Enable Tracking", ("Yes", "No"))  # Enable object tracking
    
        # Sliders for model parameters
        self.conf = float(self.st.sidebar.slider("Confidence Threshold", 0.0, 1.0, self.conf, 0.01))
        self.iou = float(self.st.sidebar.slider("IoU Threshold", 0.0, 1.0, self.iou, 0.01))
    
        col1, col2 = self.st.columns(2)
        self.org_frame = col1.empty()
        self.ann_frame = col2.empty()


    def source_upload(self):
        """Handles image and video file uploads through the Streamlit interface."""
        self.vid_file_name = ""
    
        if self.source == "video":
            vid_file = self.st.sidebar.file_uploader("Upload Video File", type=["mp4", "mov", "avi", "mkv"])
            if vid_file is not None:
                g = io.BytesIO(vid_file.read())  # BytesIO Object
                with open("uploaded_video.mp4", "wb") as out:  # Save to temporary file
                    out.write(g.read())
                self.vid_file_name = "uploaded_video.mp4"
    
        elif self.source == "webcam":
            self.vid_file_name = 0
    
        elif self.source == "image":
            img_file = self.st.sidebar.file_uploader("Upload Image File", type=["jpg", "jpeg", "png"])
            if img_file is not None:
                self.image_data = img_file  # Store uploaded image
                

    def configure(self):
        """Configures the model and loads selected classes for inference."""
        available_models = list(GDRIVE_MODELS.keys())  # Only display trained models
        
        selected_model = self.st.sidebar.selectbox("Model", available_models)
    
        # Ensure the model is downloaded before loading
        download_from_gdrive(GDRIVE_MODELS[selected_model], selected_model)
    
        with self.st.spinner("Model is loading..."):
            self.model = YOLO(f"models/{selected_model}.pt")  
            class_names = list(self.model.names.values())  
        self.st.success("Model loaded successfully!")


    def inference(self):
        """Performs real-time object detection inference."""
        self.web_ui()  # Initialize the web interface
        self.sidebar()  # Create the sidebar
        self.source_upload()  # Upload the image or video
        self.configure()  # Configure the model
    
        if self.st.sidebar.button("Start"):
            if self.source == "image":
                if self.image_data:
                    # Read image
                    file_bytes = np.asarray(bytearray(self.image_data.read()), dtype=np.uint8)
                    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
                    # Perform inference
                    results = self.model(image, conf=self.conf, iou=self.iou, classes=self.selected_ind)
                    annotated_image = results[0].plot()
    
                    # Display the results
                    self.org_frame.image(image, channels="BGR", caption="Original Image")
                    self.ann_frame.image(annotated_image, channels="BGR", caption="Detected Image")
    
            elif self.source in ["video", "webcam"]:
                stop_button = self.st.button("Stop")  # Button to stop inference
                cap = cv2.VideoCapture(self.vid_file_name)  # Capture video
                if not cap.isOpened():
                    self.st.error("Could not open video/webcam.")
                while cap.isOpened():
                    success, frame = cap.read()
                    if not success:
                        self.st.warning("Failed to read frame.")
                        break
    
                    # Perform inference
                    if self.enable_trk == "Yes":
                        results = self.model.track(frame, conf=self.conf, iou=self.iou, classes=self.selected_ind, persist=True)
                    else:
                        results = self.model(frame, conf=self.conf, iou=self.iou, classes=self.selected_ind)
                    
                    annotated_frame = results[0].plot()
    
                    if stop_button:
                        cap.release()  # Stop video capture
                        self.st.stop()  # Stop Streamlit app
    
                    self.org_frame.image(frame, channels="BGR")  # Show original frame
                    self.ann_frame.image(annotated_frame, channels="BGR")  # Show processed frame
    
                cap.release()  # Release video capture
            cv2.destroyAllWindows()  # Close any OpenCV windows



if __name__ == "__main__":
    import sys  # Import the sys module for accessing command-line arguments

    # Check if a model name is provided as a command-line argument
    args = len(sys.argv)
    model = sys.argv[1] if args > 1 else None  # assign first argument as the model name
    # Create an instance of the Inference class and run inference
    Inference(model=model).inference()
