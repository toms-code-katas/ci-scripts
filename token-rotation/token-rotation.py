import argparse
import os


def create_artifactory_token():
    pass


def update_gitlab_cicd_variable():
    pass


def create_artifactory_group(group_name: str):
    pass


def create_artifactory_permission_target(group_name: str, repo_name: str):
    pass


def parse_args():
    parser = argparse.ArgumentParser(description='Creates a read-only token for an Artifactory repository'
                                                 'and adds it as CI/CD variable named BACKUP_TOKEN to a GitLab project')
    parser.add_argument('--artifactory-admin-token', '-at', nargs='?', dest="artifactory_admin_token", required=True,
                        help='Artifactory admin token', default=os.environ.get('ARTIFACTORY_TOKEN'))
    parser.add_argument('--gitlab-admin-token', '-gt', nargs='?', dest="gitlab_admin_token", required=True,
                        help='Artifactory admin token', default=os.environ.get('GITLAB_TOKEN'))
    parser.add_argument('--artifactory-repo-name', '-arn', nargs='?', dest="artifactory_repo_name", required=True,
                        help='The name of the artifactory repository to backup')
    parser.add_argument('--gitlab-project-name', '-gpn', nargs='?', dest="gitlab_project_name", required=True,
                        help='The name of the gitlab project to add the variable to')
    parser.add_argument('--artifactory-api-url', '-aau', nargs='?', dest="artifactory_api_url", required=True,
                        help='url of the Artifactory API', default=os.environ.get('ARTIFACTORY_API_URL'))
    parser.add_argument('--gitlab-api-url', '-gau', nargs='?', dest="gitlab_api_url", required=True,
                        help='The name of the gitlab project to add the variable to')

    arguments = parser.parse_args()
    return arguments


if __name__ == '__main__':
    args = parse_args()
