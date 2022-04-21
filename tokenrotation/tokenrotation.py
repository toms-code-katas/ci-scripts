import urllib.parse
from requests import Session
from setup import parse_args


def create_artifactory_backup_token(group_name: str, art_session: Session, art_api_url) -> str:
    url: str = f"{art_api_url}/security/token"
    old_content_type = art_session.headers.pop('content-type')
    art_session.headers.update({'User-Agent': 'Mozilla/5.0'})
    resp = art_session.post(url=url,
                            data={"username": f"{group_name}-user", "scope": f"member-of-groups:{group_name}",
                                  "expires_in": 300})
    assert resp.ok
    art_session.headers.update({'content-type': old_content_type})
    return resp.json()["access_token"]


def update_gitlab_cicd_variable(project_name: str, backup_token: str, environment: str, gitlab_session: Session,
                                gitlab_url: str):
    url: str = f"{gitlab_url}/projects/{urllib.parse.quote_plus(project_name)}/variables/BACKUP_TOKEN"
    resp = gitlab_session.put(url=url, json={"key": "BACKUP_TOKEN", "value": backup_token, "masked": "true",
                                             "environment_scope": environment})
    assert resp.ok


def create_artifactory_group(group_name: str, art_session: Session, art_api_url: str):
    url: str = f"{art_api_url}/security/groups/{group_name}"
    resp = art_session.put(url=url, json={"name": group_name})
    assert resp.ok


def create_artifactory_permission_target(repo_name: str, art_session: Session,
                                         art_api_url: str):
    url: str = f"{art_api_url}/security/permissions/{repo_name}-permissions"
    resp = art_session.put(url=url, json={"name": f"{repo_name}-permissions", "repositories": [repo_name],
                                          "principals": {"groups": {repo_name: ["r"]}}})
    assert resp.ok


def create_artifactory_session(admin_token: str) -> Session:
    session = Session()
    session.headers.update(
        {"X-JFrog-Art-Api": admin_token, "content-type": "application/json"})
    return session


def create_gitlab_session(admin_token: str) -> Session:
    session = Session()
    session.headers.update(
        {"PRIVATE-TOKEN": admin_token, "content-type": "application/json"})
    return session


def main():
    args = parse_args()
    artifactory_session = create_artifactory_session(args.artifactory_admin_token)
    create_artifactory_group(args.artifactory_repo_name, artifactory_session, args.artifactory_api_url)
    create_artifactory_permission_target(args.artifactory_repo_name, artifactory_session, args.artifactory_api_url)
    backup_token = create_artifactory_backup_token(args.artifactory_repo_name, artifactory_session,
                                                   args.artifactory_api_url)
    gitlab_session = create_gitlab_session(args.gitlab_admin_token)
    update_gitlab_cicd_variable(args.gitlab_project_name, backup_token, args.gitlab_environment, gitlab_session,
                                args.gitlab_api_url)


if __name__ == '__main__':
    main()
