import argparse
import os


# Thanks to https://stackoverflow.com/a/10551190
# and https://gist.github.com/orls/51525c86ee77a56ad396#file-envdefault-py
class EnvDefault(argparse.Action):
    def __init__(self, envvar, required=True, default=None, **kwargs):
        if not default and envvar:
            if envvar in os.environ:
                default = os.environ[envvar]
        if required and default:
            required = False
        super(EnvDefault, self).__init__(default=default, required=required,
                                         **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


def parse_args():
    parser = argparse.ArgumentParser(description='Creates a read-only token for an Artifactory repository'
                                                 'and adds it as CI/CD variable named BACKUP_TOKEN to a GitLab project')
    parser.add_argument('--artifactory-admin-token', '-at', nargs='?', dest="artifactory_admin_token", required=True,
                        help='Artifactory admin token', action=EnvDefault, envvar='ARTIFACTORY_TOKEN')
    parser.add_argument('--gitlab-admin-token', '-gt', nargs='?', dest="gitlab_admin_token", required=True,
                        action=EnvDefault,
                        help='GitLab admin token', envvar='GITLAB_TOKEN')
    parser.add_argument('--artifactory-repo-name', '-arn', nargs='?', dest="artifactory_repo_name", required=True,
                        help='The name of the artifactory repository to backup')
    parser.add_argument('--gitlab-project-name', '-gpn', nargs='?', dest="gitlab_project_name", required=True,
                        help='The name of the gitlab project to add the variable to', action=EnvDefault,
                        envvar='CI_PROJECT_PATH')
    parser.add_argument('--artifactory-api-url', '-aau', nargs='?', dest="artifactory_api_url", required=True,
                        help='url of the Artifactory API', action=EnvDefault, envvar='ARTIFACTORY_API_URL')
    parser.add_argument('--gitlab-api-url', '-gau', nargs='?', dest="gitlab_api_url", required=True,
                        help='The name of the gitlab project to add the variable to', action=EnvDefault,
                        envvar='CI_API_V4_URL')
    parser.add_argument('--gitlab-environment', '-env', nargs='?', dest="gitlab_environment", required=True,
                        help='The GitLab environment to add the backup token to', action=EnvDefault,
                        envvar='CI_ENVIRONMENT_NAME')

    arguments = parser.parse_args()

    return arguments
