import sys
import gitlab
# This script checks:
# - if a gitlab repo contains a protected branch
# - if that branch is protected against force pushes
# - if that branch needs code owner approval
# - if that branch can only be merged members of the project with a specific role
# - if that branch can only be pushed to by members of the project with a specific role


def get_gitlab_project_by_path(path, gitlab_instance):
    """Get a gitlab project by path."""
    try:
        # url encode the path
        path = path.replace('/', '%2F')
        project = gitlab_instance.projects.get(id=path)
        return project
    except gitlab.exceptions.GitlabGetError as e:
        print(f'An error occurred while getting the project: {e}')
        return None

def get_protected_branches(project):
    """Get a list of protected branches."""
    return project.protectedbranches.list()

def check_allow_force_push(protected_branch):
    """Check if force pushes are allowed."""
    return protected_branch.allow_force_push

def check_code_owner_approval(protected_branch):
    """Check if code owner approval is required."""
    return protected_branch.code_owner_approval_required

def check_allowed_to_push_access_levels(protected_branch, role):
    """Check if the push access level is set to the specified role.
    Note that the role is an integer. E.g. 40 for maintainer.
    """
    return check_access_levels(protected_branch.push_access_levels, role)

def check_merge_access_levels(protected_branch, role):
    """Check if the merge access level is set to the specified role.
    Note that the role is an integer. E.g. 40 for maintainer.
    """
    return check_access_levels(protected_branch.merge_access_levels, role)

def check_access_levels(access_level_list, role):
    """Check if the access level is set to the specified role.
    Note that the role is an integer. E.g. 40 for maintainer.
    """
    found_appropriate_access_level = False
    for access_level in access_level_list:
        current_access_level = int(access_level['access_level'])
        if current_access_level >= role or current_access_level == 0:
            found_appropriate_access_level = True

    return found_appropriate_access_level

def check_protected_branches(project, role, expected_number_of_protected_branches):
    protected_branches = get_protected_branches(project)
    number_of_matching_protected_branches = 0
    for branch in protected_branches:
        branch_is_ok = True
        if check_allow_force_push(branch):
            print(f'Force pushes should not be allowed for branch {branch.name}')
            branch_is_ok = False
        if not check_code_owner_approval(branch):
            print(f'Code owner approval should be required for branch {branch.name}')
            branch_is_ok = False
        if not check_allowed_to_push_access_levels(branch, role):
            print(f'Only members of the project with at least access level {role} should be able to push to branch {branch.name}')
            branch_is_ok = False
        if not check_merge_access_levels(branch, role):
            print(f'Only members of the project with at least access level {role} should be able to merge on {branch.name}')
            branch_is_ok = False

        if branch_is_ok:
            print(f'Branch {branch.name} does meet the policy requirements')
            number_of_matching_protected_branches += 1
        else:
            print(f'Branch {branch.name} does not meet the policy requirements')

    if number_of_matching_protected_branches != expected_number_of_protected_branches:
        print(f'Expected {expected_number_of_protected_branches} protected branches matching policy requirements, but found {number_of_matching_protected_branches}')
        return False
    return True

if __name__ == '__main__':
    url = sys.argv[1]
    private_token = sys.argv[2]
    gitlab_project_path = sys.argv[3]
    expected_number_of_protected_branches = int(sys.argv[4])
    role = int(sys.argv[5])

    gitlab_instance = gitlab.Gitlab(url, private_token)
    project = get_gitlab_project_by_path(gitlab_project_path, gitlab_instance)
    if project is None:
        print(f'Could not find project {gitlab_project_path}')
        sys.exit(1)

    if not check_protected_branches(project, role, expected_number_of_protected_branches):
        print(f'Project {gitlab_project_path} does not meet the policy requirements')
        sys.exit(1)