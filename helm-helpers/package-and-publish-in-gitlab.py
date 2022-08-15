import os
import subprocess
import sys
import yaml


def add_dependency_repositories(chart_yaml: str):
    for dependency in chart_yaml["dependencies"]:
        subprocess.run(['helm', 'repo', 'add', dependency["name"], dependency["repository"]], check=True)
        print(f'\033[92m\U00002714 successfully added helm repository {dependency["name"]}\033[0m')


if __name__ == '__main__':

    with open(f'{os.getenv("CI_PROJECT_PATH")}/{sys.argv[1]}/Chart.lock', 'r') as chart_file:
        chart_yaml = yaml.safe_load(chart_file)

    add_dependency_repositories(chart_yaml)
