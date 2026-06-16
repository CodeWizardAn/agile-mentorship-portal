import cloudinary
import cloudinary.uploader
from cloudinary_config import *

result = cloudinary.uploader.upload("test.jpg")

print("Upload successful!")
print(result["secure_url"])