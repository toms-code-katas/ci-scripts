import os
import re
import requests
import subprocess
import sys
import yaml

from requests.auth import HTTPBasicAuth


def add_dependency_repositories(chart_yaml: str):
    for dependency in chart_yaml["dependencies"]:
        subprocess.run(['helm', 'repo', 'add', dependency["name"], dependency["repository"]], check=True)
        print(f'\033[92m\U00002714 Successfully added helm repository {dependency["name"]}\033[0m')


def update_dependencies():
    subprocess.run(['helm', 'dependency', 'update'], check=True)
    print(f'\033[92m\U00002714 Successfully updated dependencies \033[0m')


def build_dependencies():
    subprocess.run(['helm', 'dependency', 'build'], check=True)
    print(f'\033[92m\U00002714 Successfully built dependencies \033[0m')


def package_chart() -> str:
    package_output = subprocess.run(['helm', 'package', '.'], check=True, capture_output=True)

    chart_file_name = re.search('[^/]+$', package_output.stdout.decode("utf-8").strip()).group(0)

    print(f'\033[92m\U00002714 Successfully packaged chart and saved it to {chart_file_name} \033[0m')
    return chart_file_name


def upload_chart(helm_package_file_name):
    url = f'{os.getenv("CI_API_V4_URL")}/projects/{os.getenv("CI_PROJECT_ID")}/packages/helm/api/stable/charts'
    files = {'chart': open(helm_package_file_name, 'rb')}
    response = requests.post(url, files=files, auth=HTTPBasicAuth('gitlab-ci-token', os.getenv("CI_JOB_TOKEN")))
    if not response.ok:
        raise Exception(f"Could not upload chart: {response.status_code}")
    else:
        print(f'\033[92m\U00002714 Successfully uploaded chart \033[0m')


if __name__ == '__main__':

    chart_path = f'{os.getenv("CI_PROJECT_DIR")}/{sys.argv[1]}'
    os.chdir(chart_path)

    with open(f'Chart.lock', 'r') as chart_file:
        chart_yaml = yaml.safe_load(chart_file)

    add_dependency_repositories(chart_yaml)
    build_dependencies()
    helm_package_file_name = package_chart()
    upload_chart(helm_package_file_name)
