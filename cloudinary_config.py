import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name = "djcbdezzq",
    api_key = "738535574236412",
    api_secret = "60Lof3kDlcBJJLw4L0vgz4a05fY"
)

def upload_file(file_bytes, folder="agilementor", resource_type="auto"):
    result = cloudinary.uploader.upload(
        file_bytes,
        folder=folder,
        resource_type=resource_type
    )
    return result["secure_url"]