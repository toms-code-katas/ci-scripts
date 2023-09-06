import base64
import logging
import os
from pathlib import Path
import sys
import yaml

from datetime import datetime
import pexpect

logging.basicConfig(
    level=logging.DEBUG,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def generate_new_key() -> str:
    logger.info("\033[1;36mGenerating new key\033[0m")
    age_command = pexpect.spawn("age-keygen")
    age_command.expect(pexpect.EOF)
    age_command.close()
    assert age_command.exitstatus == 0, "Failed to generate new key"
    key = age_command.before.decode("utf-8")
    public_key = key.splitlines()[1].split(": ")[1]
    logger.info(f"\033[1;92m\U00002714 Successfully generated new key pair with public key {public_key}\033[0m")
    return key


def create_and_encrypt_new_key_file(key:str, cluster, password: str):
    key_file_name = datetime.now().strftime(f"{os.getcwd()}/identity.agekey.%Y-%m-%d-%H-%M.{cluster}")
    with open(key_file_name, "w") as kf:
        kf.write(key)
    logger.info(f"\033[1;36mEncrypting key file {key_file_name}\033[0m")
    encrypt_command = pexpect.spawn(f"age -a -p {key_file_name}")
    encrypt_command.logfile_read = sys.stdout.buffer
    encrypt_command.expect("Enter.*")
    encrypt_command.sendline(password)
    encrypt_command.expect("Confirm.*")
    encrypt_command.sendline(password)
    encrypt_command.expect("\r\n")
    encrypt_command.expect(pexpect.EOF)
    with open(key_file_name + ".enc", "wb") as kf:
        kf.write(encrypt_command.before)
    encrypt_command.close()
    assert encrypt_command.exitstatus == 0, "Failed to encrypt key file"
    logger.info(f"\033[1;92m\U00002714 Successfully encrypted key file {key_file_name}\033[0m")
    os.remove(key_file_name)


def get_sops_config_file(secret_repo_path: str) -> str:
    config_file = os.path.join(secret_repo_path, ".sops.yaml")
    logger.info(f"\033[1;36mFound sops config file {config_file} for cluster {cluster}\033[0m")
    return config_file

def get_secret_location(cluster: str, secret_repo_path) -> str:
    with open(os.path.join(os.getcwd(), "secret-locations.yaml")) as f:
        secret_locations = yaml.safe_load(f)
    secret_location = os.path.join(secret_repo_path, secret_locations[cluster])
    logger.info(f"\033[1;36mFound secret location {secret_location} for cluster {cluster}\033[0m")
    return secret_location

def generate_k8s_secret(cluster: str, secret_repo_path: str, key: str) -> str:
    logger.info(f"\033[1;36mGenerating k8s secret for cluster {cluster}\033[0m")
    k8s_secret_location = get_secret_location(cluster, secret_repo_path)
    path = Path(k8s_secret_location).stem
    name, namespace = path.split("_")
    secret_as_dict = {
        "apiVersion": "v1",
        "kind": "Secret",
        "type": "Opaque",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "data": {
            "identity.agekey": base64.b64encode(key.encode("utf-8")).decode("utf-8")
        }
    }
    with open(k8s_secret_location, "w") as f:
        yaml.safe_dump(secret_as_dict, f)
    logger.info(f"\033[1;92m\U00002714 Successfully generated k8s secret {k8s_secret_location}\033[0m")
    return k8s_secret_location


def encrypt_k8s_secret(k8s_secret_location: str, cluster: str, secret_repo_path: str):
    logger.info(f"\033[1;36mEncrypting k8s secret {k8s_secret_location}\033[0m")
    encrypt_command = pexpect.spawn(f"sops --verbose --encrypt --config {get_sops_config_file(secret_repo_path)} -i {k8s_secret_location}")
    encrypt_command.logfile_read = sys.stdout.buffer
    encrypt_command.expect(pexpect.EOF)
    encrypt_command.close()
    assert encrypt_command.exitstatus == 0, "Failed to encrypt k8s secret"
    logger.info(f"\033[1;92m\U00002714 Successfully encrypted k8s secret {k8s_secret_location}\033[0m")


if __name__ == '__main__':
    cluster = sys.argv[1]
    secret_repo_path = sys.argv[2]
    key_password = sys.argv[3]

    new_key = generate_new_key()
    create_and_encrypt_new_key_file(new_key, cluster, key_password)
    k8s_secret_location = generate_k8s_secret(cluster, secret_repo_path, new_key)
    encrypt_k8s_secret(k8s_secret_location, cluster, secret_repo_path)