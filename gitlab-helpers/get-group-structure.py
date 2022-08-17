import gitlab
import os
import time

gl: gitlab.Gitlab
trace_size_limit = 1000
repository_size_limit = 1048576


def get_gitlab_group(group_id):
    return gl.groups.get(group_id)


def traverse_all_projects_in_group(group_id: str, functions):
    group = get_gitlab_group(group_id)
    for group_project in group.projects.list(get_all=True):
        project = gl.projects.get(id=group_project.id, statistics=True)
        for f in functions:
            f(project)

    for sub_group in group.subgroups.list(get_all=True):
        traverse_all_projects_in_group(sub_group.id, functions)


def trace_exists_and_does_not_exceed_size_limit(job, size_limit_in_bytes):
    for artifact in job.attributes["artifacts"]:
        if artifact["file_type"] == "trace" and artifact["size"] <= size_limit_in_bytes:
            return True
    return False


def export_repository(project):
    global repository_size_limit
    repository_size = project.statistics["repository_size"]
    if repository_size > repository_size_limit:
        print(f"repository size {repository_size} is bigger than size limit {repository_size_limit}. Project is not "
              f"exported")
        return

    export = project.exports.create()

    export.refresh()
    while export.export_status != 'finished':
        time.sleep(1)
        print(f"Export of project {project.id} not yet finished")
        export.refresh()

    with open(f'/tmp/{project.id}.tgz', 'wb') as f:
        export.download(streamed=True, action=f.write)


def get_jobs_traces(project):
    global trace_size_limit
    for job in project.jobs.list(get_all=True):
        if trace_exists_and_does_not_exceed_size_limit(job, trace_size_limit):
            print(job.trace().decode("utf-8"))
        else:
            print("trace exceeds size limit")


if __name__ == '__main__':
    gl = gitlab.Gitlab(url='https://gitlab.com', private_token=os.getenv("GITLAB_TOKEN"))
    traverse_all_projects_in_group(os.getenv("GITLAB_GROUP_ID"), functions=[get_jobs_traces, export_repository])
