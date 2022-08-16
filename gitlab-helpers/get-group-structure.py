import gitlab
import os
from gitlab.v4.objects.groups import Group

gitlab_server: gitlab.Gitlab


def get_gitlab_group(group_id):
    return gitlab_server.groups.get(group_id)


if __name__ == '__main__':
    gitlab_server = gitlab.Gitlab(url='https://gitlab.com', private_token=os.getenv("GITLAB_TOKEN"))
    group: Group = get_gitlab_group(os.getenv("GITLAB_GROUP_ID"))

    while group:
        for group_project in group.projects.list(get_all=True):
            project_id = group_project.id
            project = gitlab_server.projects.get(id=project_id)
            for job in project.jobs.list(get_all=True):
                print(job.name)
                print(job.trace().decode("utf-8"))
        group = None


