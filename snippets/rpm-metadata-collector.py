# A simple script for getting rpm metadata from artifactory
import sys

import requests


def get_artifact_names_from_artifactory_repository(url, repository_name, api_key, session=None):
    repo_url = f"{url}/{repository_name}"
    if session:
        response = session.get(repo_url)
    else:
        response = requests.get(repo_url, headers={"X-JFrog-Art-Api": api_key})
    response.raise_for_status()
    json_response = response.json()
    artifact_names = []
    for child in json_response["children"]:
        if not child["folder"] and child["uri"].endswith(".rpm"):
            artifact_names.append(repository_name + child["uri"])
        elif child["folder"]:
            artifact_names.extend(get_artifact_names_from_artifactory_repository(url, f"{repository_name}/{child['uri']}", api_key, session))
    return artifact_names


# This method displays the following information for an artifact:
# - name
# - path
# - size
# - createdBy
# - modifiedBy
# - size
# In addition the following properties are displayed:
# - rpm.metadata.name
# - rpm.metadata.version
def get_artifact_metadata(url, artifact_path, api_key, session=None):
    repo_url = f"{url}/{artifact_path}"

    response = do_get(api_key, session, repo_url)

    response.raise_for_status()
    json_response = response.json()

    # Create a one line output separated by commas
    line = f"{json_response['path']}, {json_response['size']}, {json_response['createdBy']}, {json_response['modifiedBy']}, {json_response['checksums']['sha1']}"

    repo_url = repo_url + "?properties"
    response = session.get(repo_url)
    json_response = response.json()

    for property in json_response["properties"]:
        if property == "rpm.metadata.name":
            line = line + f", {json_response['properties'][property][0]}"
        elif property == "rpm.metadata.version":
            line = line + f", {json_response['properties'][property][0]}"

    return line


def do_get(api_key, session, url):
    if session:
        response = session.get(url)
    else:
        response = requests.get(url, headers={"X-JFrog-Art-Api": api_key})
    return response


# This method creates a session for the artifactory rest api which can be used for multiple requests
def create_artifactory_session(api_key):
    session = requests.Session()
    session.headers.update({"X-JFrog-Art-Api": api_key})
    return session


if __name__ == '__main__':
    url = sys.argv[1]
    api_key = sys.argv[2]
    repo_name = sys.argv[3]
    session = create_artifactory_session(api_key)
    all_artifacts = (get_artifact_names_from_artifactory_repository(url, repo_name, api_key, session))

    # Print a header line
    print("path, size, createdBy, modifiedBy, sha1, rpm.metadata.name, rpm.metadata.version")
    print("--------------------------------------------------------------------------------")

    for artifact in all_artifacts:
        print(get_artifact_metadata(url, artifact, api_key, session))