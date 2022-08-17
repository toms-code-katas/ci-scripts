import json
import gitlab
import os

gitlab_server: gitlab.Gitlab


def get_gitlab_group(group_id):
    return gitlab_server.groups.get(group_id)


def get_traces(group_id: str, size_limit_in_bytes: int):
    group = get_gitlab_group(group_id)
    for group_project in group.projects.list(get_all=True):
        for job in gitlab_server.projects.get(id=group_project.id).jobs.list(get_all=True):
            if trace_exists_and_does_not_exceed_size_limit(job, size_limit_in_bytes):
                print(job.trace().decode("utf-8"))
            else:
                print("trace exceeds size limit")

    for sub_group in group.subgroups.list(get_all=True):
        get_traces(sub_group.id)


def trace_exists_and_does_not_exceed_size_limit(job, size_limit_in_bytes):
    for artifact in job.attributes["artifacts"]:
        if artifact["file_type"] == "trace" and artifact["size"] <= size_limit_in_bytes:
            return True
    return False


if __name__ == '__main__':
    gitlab_server = gitlab.Gitlab(url='https://gitlab.com', private_token=os.getenv("GITLAB_TOKEN"))
    get_traces(os.getenv("GITLAB_GROUP_ID"), 2000)
