import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import os

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def upload_file(file_bytes, folder="agilementor", resource_type="auto"):
    result = cloudinary.uploader.upload(
        file_bytes, folder=folder, resource_type=resource_type
    )
    return result["secure_url"]