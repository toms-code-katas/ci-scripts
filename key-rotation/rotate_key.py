import gitlab
import glob
import logging
from io import BytesIO
import os
import pexpect
import re
import subprocess
import sys
import tempfile
import zipfile
import yaml

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def get_last_keys_from_artifacts(project, environment, number_of_keys=20):
    environment_age_keys_found = {}
    keys_found = 0
    logger.info(f"\033[1;36mLooking for last {number_of_keys} age keys in {environment} environment\033[0m")
    for pipeline in project.pipelines.list(get_all=True):
        for pipeline_job in pipeline.jobs.list(order_by="finished_at", scope='success', get_all=True):
            for artifact in pipeline_job.attributes["artifacts"]:
                try:
                    artifact_environment = re.search("(?<=agekeys-).*(?=.zip)", artifact["filename"]).group(0)
                    if artifact_environment == environment:
                        job = project.jobs.get(pipeline_job.id, lazy=True)
                        logger.info(
                            f"\033[1;36mArtifact {artifact['filename']} of job {pipeline_job.id} is matching {environment} environment\033[0m")
                        add_keys_from_zip(environment_age_keys_found, job)
                        keys_found = keys_found + 1
                        if keys_found == number_of_keys:
                            logger.info(f"\033[1;36m{number_of_keys} keys collected for environment {environment}\033[0m")
                            return environment_age_keys_found
                except AttributeError:
                    pass
    logger.info(f"\033[1;36m{number_of_keys} keys collected for environment {environment}\033[0m")
    return environment_age_keys_found


def add_keys_from_zip(environment_age_keys_found, job):
    output = BytesIO()
    job.artifacts(streamed=True, action=output.write)
    output.flush()
    zip = zipfile.ZipFile(output)
    for name in zip.namelist():
        logger.info(f"\033[1;36mFound zip file entry {name}\033[0m")
        environment_age_keys_found.update({name: zip.read(name)})


def decrypt_key(key, keyfile, password):
    with open(keyfile, "wb") as kf:
        kf.write(key)

    age = pexpect.spawn(f"age -d {keyfile}")
    age.expect('Enter.*')
    age.sendline(password)
    age.expect(r'# created\s*:\s*(.*)')
    key_found = age.after.decode('utf-8')

    # Remove empty lines
    key_found = os.linesep.join([s for s in key_found.splitlines() if s])

    with open(keyfile + ".txt", "wt") as kf:
        kf.write(key_found)

    return keyfile + ".txt"


def get_current_age_key_from_sops_config(sops_config_file_path):
    with open(sops_config_file_path, 'r') as sops_config_file:
        sops_config = yaml.load(sops_config_file, Loader=yaml.FullLoader)

    current_age_key = None
    for creation_rule in sops_config["creation_rules"]:
        creation_rule_age_key = creation_rule["age"]
        logger.info(f"\033[1;36mFound age key {creation_rule_age_key} for creation rule {creation_rule['path_regex']}\033[0m")
        if not current_age_key:
            logger.info(f"\033[1;36mSetting current age key to {creation_rule_age_key}\033[0m")
            current_age_key = creation_rule_age_key
        elif current_age_key and creation_rule_age_key != current_age_key:
            logger.error(f"\033[1;31mFound different age key {creation_rule_age_key} in sops config file\033[0m")
            raise Exception("Creation rules with different keys detected")

    if not current_age_key:
        logger.error(f"\033[1;31mNo age key found in sops config file\033[0m")
        raise Exception(f"No age keys found in sops configuration file {sops_config_file_path}")

    logger.info(f"\033[1;92m\U00002714 Found current age key {current_age_key}\033[0m")
    return current_age_key


def replace_age_key_in_sops_config(sops_config_file_path, old_key, new_key):
    with open(sops_config_file_path, 'r') as sops_config_file:
        sops_config = yaml.load(sops_config_file, Loader=yaml.FullLoader)

    for creation_rule in sops_config["creation_rules"]:
        creation_rule_age_key = creation_rule["age"]
        if not creation_rule_age_key:
            raise Exception("Creation rules without key detected")
        elif creation_rule_age_key != old_key:
            raise Exception("Creation rules key differs from old key")
        else:
            creation_rule["age"] = new_key

    with open(sops_config_file_path, 'w') as sops_config_file:
        yaml.dump(data=sops_config, stream=sops_config_file, sort_keys=False)


def get_pub_key_from_key_file(key_file_path):
    with open(key_file_path) as key_file:
        for line in key_file:
            match = re.search(pattern="(?<=public key: ).*", string=line)
            if match:
                return match.group(0)


def decrypt_secret(keyfile, secret_file):
    env = os.environ.copy()
    env["SOPS_AGE_KEY_FILE"] = keyfile
    subprocess.run(
        [f"sops", "-d", "-i", secret_file], check=True, env=env)


def encrypt_secret(secret_file):
    cwd = os.path.dirname(secret_file)
    env = os.environ.copy()
    subprocess.run(
        [f"sops", "-e", "-i", secret_file], check=True, env=env, cwd=cwd)


def get_encrypted_files(secrets_folder):
    pattern = "(?:(?<=recipient=)|(?<=recipient: )).*"
    encrypted_files = []
    for file in glob.iglob(secrets_folder + '/**/*.*', recursive=True):
        with open(file) as file_content:
            for line in file_content:
                match = re.search(pattern=pattern, string=line)
                if match:
                    encrypted_files.append(file)
                    break
    return encrypted_files


def silent_remove(filenames):
    for filename in filenames:
        if not filename:
            continue
        try:
            os.remove(filename)
        except OSError:
            pass


def get_key_file_for_pub_key(cluster_keys_found, pub_key):
    sorted_keys = sorted(cluster_keys_found, reverse=True)
    for key_name in sorted_keys:
        key = cluster_keys_found[key_name]
        encrypted_key_file = tempfile.NamedTemporaryFile(prefix="key-").name
        decrypted_key_file = decrypt_key(key, encrypted_key_file, os.getenv("KEY_PASSWORD"))
        if not decrypted_key_file and os.getenv("OLD_KEY_PASSWORD"):
            print(f"key password was incorrect. Trying old password")
            decrypted_key_file = decrypt_key(key, encrypted_key_file, os.getenv("OLD_KEY_PASSWORD"))
            if not decrypted_key_file:
                print(f"old key password was incorrect. Aborting")
                raise Exception("No correct password found")
        elif not decrypted_key_file:
            print(f"key password was incorrect and no old key was provided. Aborting")
            raise Exception("Key password incorrect")

        other_pub_key = get_pub_key_from_key_file(decrypted_key_file)
        if pub_key == other_pub_key:
            silent_remove([encrypted_key_file])
            return decrypted_key_file
        else:
            silent_remove([encrypted_key_file, decrypted_key_file])


if __name__ == '__main__':
    encrypted_new_key_file = None
    decrypted_new_key_file = None
    decrypted_old_key_file = None
    try:
        # Use PERSONAL_ACCESS_TOKEN as private token for api
        # Use CI_SERVER_URL='https://gitlab.com' as url
        # Use CI_PROJECT_ID='9999' as project where the keys are stored
        # Use CLUSTER as the environment
        # Use KEY_PASSWORD for the password of the two keys
        # Use OLD_KEY_PASSWORD for the old password in case of a password change
        # Use SECRETS_DIR as folder containing the encrypted secrets

        cluster = os.getenv("CLUSTER")
        sops_config_file_path = f"{os.getenv('SECRETS_DIR')}/.sops.yaml"

        logger.info(f"\033[1;36mLooking for current age key in sops config file {sops_config_file_path}\033[0m")
        current_configured_pub_key = get_current_age_key_from_sops_config(sops_config_file_path)

        gl = gitlab.Gitlab(url=os.getenv("CI_SERVER_URL"), private_token=os.getenv("PERSONAL_ACCESS_TOKEN"))
        project = gl.projects.get(id=os.getenv("CI_PROJECT_ID"))

        logger.info(f"\033[1;36mLooking for last created private key for re-encryption\033[0m")
        cluster_keys_found = get_last_keys_from_artifacts(project, cluster)
        decrypted_old_key_file = get_key_file_for_pub_key(cluster_keys_found, current_configured_pub_key)

        last_key_file = glob.glob(f'{os.getenv("CI_PROJECT_DIR")}/identity.agekey.*')

        if not last_key_file:
            print("No new key file found as an artifact. Using last artifact uploaded")
            sorted_keys = sorted(cluster_keys_found, reverse=True)
            new_key = cluster_keys_found[sorted_keys[0]]
        else:
            print(f"New key file {last_key_file[0]} found")
            with open(f'{last_key_file[0]}', 'rb') as file:
                new_key = file.read()

        encrypted_new_key_file = tempfile.NamedTemporaryFile(prefix="new_key-").name
        decrypted_new_key_file = decrypt_key(new_key, encrypted_new_key_file, os.getenv("KEY_PASSWORD"))

        old_key_pub_key = get_pub_key_from_key_file(decrypted_old_key_file)

        if not current_configured_pub_key == old_key_pub_key:
            raise Exception("Currently configured age key is not the same as the old key")

        secret_files = get_encrypted_files(os.getenv('SECRETS_DIR'))
        for encrypted_file in secret_files:
            decrypt_secret(decrypted_old_key_file, encrypted_file)

        new_key_pub_key = get_pub_key_from_key_file(decrypted_new_key_file)
        replace_age_key_in_sops_config(sops_config_file_path, old_key_pub_key, new_key_pub_key)

        for encrypted_file in secret_files:
            encrypt_secret(encrypted_file)
    finally:
        silent_remove([encrypted_new_key_file, decrypted_new_key_file, decrypted_old_key_file])
