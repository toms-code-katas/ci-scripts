"""
This script checks all access tokens for nearing expiration date.
"""
import datetime
import sys

import gitlab


def connect_to_gitlab(url, token):
    """
    Connect to GitLab instance.
    :param url: The URL of the GitLab instance.
    :param token: The access token for the GitLab instance. Requires full api scope.
    :return: A GitLab instance.
    """
    return gitlab.Gitlab(url, private_token=token)


def check_all_access_tokens(project_or_group):
    """
    Check all access tokens for a project or group.
    :param project_or_group: The project or group to check.
    :return: A list of expired access tokens or tokens nearing expiration date.
    """
    expired_project_or_group_tokens = []

    is_group = True
    if isinstance(project_or_group, gitlab.v4.objects.GroupProject):
        complete_project_or_group = gl.projects.get(project_or_group.id)
        is_group = False
    else:
        complete_project_or_group = gl.groups.get(project_or_group.id)

    try:
        for access_token in complete_project_or_group.access_tokens.list(all=True):
            print(f"Checking token {access_token.name}")
            exp_token = is_expired(access_token)
            if exp_token:
                expired_project_or_group_tokens.append(exp_token)
                print_expired_token_details(complete_project_or_group, exp_token, is_group)
    except gitlab.exceptions.GitlabAuthenticationError:
        print(f"Could not get access tokens for {complete_project_or_group.name}. "
              f"Check if you have access to the project / group.")

    return expired_project_or_group_tokens


def print_expired_token_details(complete_project_or_group, exp_token, is_group):
    """
    Print details for an expired access token or a token nearing expiration date.
    :param complete_project_or_group: The project or group the token belongs to.
    :param exp_token: The expired access token.
    :param is_group: Boolean indicating if the parameter complete_project_or_group
    is a group or a project.
    """
    if is_group:
        print(f"Token {exp_token.name} in group {complete_project_or_group.full_path}"
              f" nears expiration date or is expired and needs to be renewed.")
    else:
        print(f"\033[91mToken {exp_token.name} in project "
              f"{complete_project_or_group.path_with_namespace}"
              f" is expired or nears expiration date and needs to be renewed.\033[0m")
    print(f"\033[91mToken details: {exp_token.attributes}\033[0m")
    print("\033[91mPlease use the same name, scopes and access level when renewing the token. "
          "For access_level to role mapping see:"
          " https://docs.gitlab.com/ee/api/access_requests.html\033[0m")


def is_expired(access_token):
    """
    Check if an access token is expired or nearing expiration date.
    :param access_token: The access token to check.
    :return: The access token if it is expired, None otherwise.
    """
    expiration_date = datetime.datetime.strptime(access_token.expires_at, "%Y-%m-%d")

    difference = expiration_date - datetime.datetime.utcnow()
    if difference.days < 90:
        print(f"\033[91mToken {access_token.name} has an expiration date of"
              f" {access_token.expires_at}"
              f" and expires in {difference.days} days.\033[0m")
        return access_token
    return None


def walk_groups_and_projects(gitlab_instance, group_path):
    """
    Walk all groups and projects in a group and check all access tokens for expiration date.
    :param gitlab_instance: The GitLab instance.
    :param group_path: The path of the group to walk.
    :return: A list of all tokens nearing expiration date or are expired.
    """
    collected_expired_tokens = []
    group = gitlab_instance.groups.get(group_path)
    print(f"Checking group '{group.full_path}' for nearly expired access tokens.")
    expired_group_or_project_tokens = check_all_access_tokens(group)
    if expired_group_or_project_tokens:
        collected_expired_tokens.append(expired_group_or_project_tokens)
    projects = group.projects.list(all=True)
    for project in projects:
        print(f"Checking project '{project.path_with_namespace}' for nearly expired access tokens.")
        expired_group_or_project_tokens = check_all_access_tokens(project)
        if expired_group_or_project_tokens:
            collected_expired_tokens.append(expired_group_or_project_tokens)
    subgroups = group.subgroups.list(all=True)
    for subgroup in subgroups:
        collected_expired_tokens.extend(walk_groups_and_projects(
            gitlab_instance, subgroup.full_path))
    return collected_expired_tokens


if __name__ == '__main__':
    # Check all access tokens for nearing expiration date starting from the path of a group.
    # Usage: python3 get_access_tokens_expiration_date.py <gitlab_url> <gitlab_token>
    # <root_group_path>
    # Example: python3 get_access_tokens_expiration_date.py https://gitlab.example.com/
    # ghjkl1234567890qwertyuiop my-root-group
    gitlab_url = sys.argv[1]
    gitlab_token = sys.argv[2]
    root_group = sys.argv[3]

    # Create a GitLab instance
    gl = connect_to_gitlab(gitlab_url, gitlab_token)

    # Get all projects and groups
    all_expired_tokens = walk_groups_and_projects(gl, root_group)
    if all_expired_tokens:
        print("\033[91mThe following access tokens are nearing expiration date"
              " and need to be renewed:")
        for expired_tokens in all_expired_tokens:
            for expired_token in expired_tokens:
                print(f"{expired_token.name}")
        print("See above for details.\033[0m")
        sys.exit(1)
    else:
        print("No access tokens are nearing expiration date.")
        sys.exit(0)
