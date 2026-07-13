import os

from cryptography.fernet import Fernet

key = os.getenv("ENCYRPTION_KEY", "")
fernet = Fernet(key)
