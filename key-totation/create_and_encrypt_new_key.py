import logging
import sys

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
    key_file_name = datetime.now().strftime(f"identity.agekey.%Y-%m-%d-%H-%M.{cluster}")
    with open(key_file_name, "w") as kf:
        kf.write(key)
    logger.info(f"\033[1;36mEncrypting key file {key_file_name}\033[0m")
    age = pexpect.spawn(f"age -a -p {key_file_name}")
    age.expect("Enter.*")
    age.sendline(password)
    age.expect("Confirm.*")
    age.sendline(password)
    age.expect("\r\n")
    with open(key_file_name + ".enc", "wb") as kf:
        kf.write(age.before)
    age.expect(pexpect.EOF)
    age.close()
    assert age.exitstatus == 0, "Failed to encrypt key file"
    logger.info(f"\033[1;92m\U00002714 Successfully encrypted key file {key_file_name}\033[0m")




def get_secret_location(cluster: str) -> str:
    pass


def generate_k8s_secret(cluster: str, key: str) -> str:
    pass


def encrypt_k8s_secret(k8s_secret_location: str):
    pass

if __name__ == '__main__':
    cluster = sys.argv[1]
    key_password = sys.argv[2]

    new_key = generate_new_key()
    create_and_encrypt_new_key_file(new_key, cluster, key_password)
    k8s_secret_location = generate_k8s_secret(cluster, new_key)
    encrypt_k8s_secret(k8s_secret_location)