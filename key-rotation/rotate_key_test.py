import os
import unittest
from rotate_key import get_encrypted_files


class TestGetEncryptedFiles(unittest.TestCase):

    def test_get_encrypted_files(self):
        secrets_folder = os.getenv("SECRETS_FOLDER")
        encrypted_files = get_encrypted_files(secrets_folder)
        assert encrypted_files == []