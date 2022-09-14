import gitlab
from io import BytesIO
import os
import re
import subprocess
import zipfile
import tempfile


def get_last_two_keys_from_artifacts(project, environment):
    environment_age_keys_found = {}
    keys_found = 0
    for pipeline in project.pipelines.list(get_all=False):
        for pipeline_job in pipeline.jobs.list(order_by="finished_at", scope='success', get_all=False):
            for artifact in pipeline_job.attributes["artifacts"]:
                try:
                    artifact_environment = re.search("(?<=agekeys-).*(?=.zip)", artifact["filename"]).group(0)
                    if artifact_environment == environment:
                        print(f"Found artifact for environment {artifact_environment}")
                        job = project.jobs.get(pipeline_job.id, lazy=True)
                        output = BytesIO()
                        job.artifacts(streamed=True, action=output.write)
                        output.flush()
                        zip = zipfile.ZipFile(output)
                        armoured_age_key = {name: zip.read(name) for name in zip.namelist()}
                        environment_age_keys_found.update(armoured_age_key)
                        keys_found = keys_found + 1
                        if keys_found == 2:
                            print(f"Found two last keys for environment {artifact_environment}")
                            return environment_age_keys_found
                except AttributeError:
                    pass


def decrypt_key(key, keyfile):
    with open(keyfile.name, "wb") as kf:
        kf.write(key)
    print(keyfile.name)
    subprocess.run(
        [f"{os.path.dirname(__file__)}/decrypt_key.sh", os.getenv("KEY_PASSWORD"), keyfile.name],
        check=True)
    return keyfile.name + ".txt"


def decrypt_secret(keyfile, secret_file):
    env =  os.environ.copy()
    env["SOPS_AGE_KEY_FILE"] = keyfile
    subprocess.run(
        [f"sops", "-d", secret_file], check=True, env=env)


if __name__ == '__main__':
    # Use CI_JOB_TOKEN='[MASKED]' as private token
    # Use CI_SERVER_URL='https://gitlab.com' as url
    # Use CI_PROJECT_ID='9999' as project id
    # Use ENVIRONMENT as the environment to use
    # Use KEY_PASSWORD for the password of the two keys
    # Use SECRETS_DIR as folder containing the encrypted secrets
    environment = os.getenv("ENVIRONMENT")
    gl = gitlab.Gitlab(url=os.getenv("CI_SERVER_URL"), private_token=os.getenv("CI_JOB_TOKEN"))

    project = gl.projects.get(id=os.getenv("CI_PROJECT_ID"))

    environment_age_keys_found = get_last_two_keys_from_artifacts(project, environment)
    sorted_keys = sorted(environment_age_keys_found)

    new_key = environment_age_keys_found[sorted_keys[0]]
    new_key_file = tempfile.NamedTemporaryFile(prefix="new_key-")
    decrypted_new_key_file = decrypt_key(new_key, new_key_file)

    old_key = environment_age_keys_found[sorted_keys[1]]
    old_key_file = tempfile.NamedTemporaryFile(prefix="old_key-")
    decrypted_old_key_file = decrypt_key(old_key, old_key_file)

