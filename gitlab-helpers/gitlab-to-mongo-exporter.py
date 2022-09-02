import datetime
import json

import gitlab
import os
import tempfile
import time

from pymongo import MongoClient


class ExportRepository:

    def __init__(self, repository_size_limit):
        self.repository_size_limit = repository_size_limit

    def process(self, project):
        repository_size = project.statistics["repository_size"]
        if repository_size > self.repository_size_limit:
            print(
                f"repository size {repository_size} is bigger than size limit"
                f" {self.repository_size_limit}. Project is not "
                f"exported")
            return

        export = project.exports.create()

        export.refresh()
        while export.export_status != 'finished':
            time.sleep(1)
            print(f"Export of project {project.id} not yet finished")
            export.refresh()

        tmp = tempfile.mkdtemp(prefix=f"{project.id}-")

        with open(f'{tmp}/{project.id}.tgz', 'wb') as f:
            export.download(streamed=True, action=f.write)


# Visitor pattern
# https://refactoring.guru/design-patterns/visitor
class GetJobsAndTraces:

    def __init__(self, latest_job_per_project: {}, trace_size_limit: int, outputs):
        self.latest_job_per_project = latest_job_per_project
        self.trace_size_limit = trace_size_limit
        self.outputs = outputs

    def process(self, project):
        updated_after = None
        if project.id in self.latest_job_per_project:
            updated_after = self.latest_job_per_project[project.id]

        for pipeline in project.pipelines.list(updated_after=updated_after, get_all=True):
            for pipeline_job in pipeline.jobs.list(get_all=True):
                if get_time(pipeline_job.created_at) > updated_after:
                    job = project.jobs.get(pipeline_job.id)
                    self.output_job_and_trace(job)

    def output_job_and_trace(self, job):
        if self.trace_exists_and_does_not_exceed_size_limit(job):
            job_as_json = self.job_to_json(job)
            for opt in self.outputs:
                opt(job_as_json, "jobs")

    def job_to_json(self, job):
        job_as_json = json.loads(job.to_json())
        job_as_json["trace"] = job.trace().decode("utf-8")
        return job_as_json

    def trace_exists_and_does_not_exceed_size_limit(self, job):
        for artifact in job.attributes["artifacts"]:
            if artifact["file_type"] == "trace" and artifact["size"] <= self.trace_size_limit:
                return True
        return False


gl: gitlab.Gitlab


def get_gitlab_group(group_id):
    return gl.groups.get(group_id)


def traverse_all_projects_in_group(group_id: str, processors):
    group = get_gitlab_group(group_id)
    for group_project in group.projects.list(get_all=True):
        project = gl.projects.get(id=group_project.id, statistics=True)
        for processor in processors:
            processor.process(project)

    for sub_group in group.subgroups.list(get_all=True):
        traverse_all_projects_in_group(sub_group.id, processors)


def get_time(latest, offset: int=0):
    latest = latest.replace("Z", "+00:00")
    return datetime.datetime.fromisoformat(latest) + datetime.timedelta(seconds=offset)


def get_latest_job_date_per_project():
    # db.jobs.aggregate([ { $group: { _id: "$pipeline.project_id", latests: { $max: "$pipeline.updated_at" } } }])
    result = {}
    for record in db["jobs"].aggregate(pipeline=[
        {
            "$group": {
                "_id": "$pipeline.project_id",
                "latest": {"$max": "$pipeline.updated_at"}
            }
        }
    ]):
        result[record["_id"]] = get_time(record["latest"])
    return result


if __name__ == '__main__':
    mongo_client = MongoClient('mongodb://localhost:27017/')
    db = mongo_client['gitlab']
    latest_job_per_project = get_latest_job_date_per_project()

    mongo_output = lambda obj_as_json, type: db[type].insert_one(obj_as_json)
    stdout_output = lambda obj_as_json, type: print(json.dumps(obj_as_json, indent=2))  # noqa

    get_jobs_and_traces = GetJobsAndTraces(latest_job_per_project=latest_job_per_project, trace_size_limit=10000,
                                           outputs=[stdout_output, mongo_output])
    repository_exporter = ExportRepository(repository_size_limit=1000000)

    gl = gitlab.Gitlab(url='https://gitlab.com', private_token=os.getenv("GITLAB_TOKEN"))
    traverse_all_projects_in_group(os.getenv("GITLAB_GROUP_ID"), processors=[get_jobs_and_traces])
