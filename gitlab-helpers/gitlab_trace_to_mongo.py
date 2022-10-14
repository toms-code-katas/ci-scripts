"""
A simple script that exports a GitLab pipeline its jobs and traces (API objects) to a mongo db.
"""
import os
from gitlab import Gitlab
from pymongo import MongoClient

if __name__ == '__main__':
    mongo_client = MongoClient(f"mongodb://{os.getenv('MONGO_DB_HOST', 'mongodb')}:27017/")
    mongo_db = mongo_client["gitlab"]

    gitlab_url = os.getenv(
        f"{os.getenv('CI_SERVER_PROTOCOL', 'https')}://{os.getenv('CI_SERVER_HOST', 'gitlab.com')}:"
        f"{os.getenv('CI_SERVER_PORT', '443')}")
    private_token = os.getenv("GITLAB_TOKEN", os.getenv("CI_JOB_TOKEN"))
    project_id = os.getenv("CI_PROJECT_ID")
    pipeline_id = os.getenv("CI_PIPELINE_ID")
    trace_size_limit = int(os.getenv("TRACE_SIZE_LIMIT", "1000000"))

    gitlab = Gitlab(url=gitlab_url, private_token=private_token)

    project = gitlab.projects.get(id=project_id)
    pipeline = project.pipelines.get(id=pipeline_id)
    collected_jobs = []

    print(f"Collecting jobs and trace logs for pipeline {pipeline.id} of project {project.id}")
    for pipeline_job in pipeline.jobs.list(get_all=True):
        complete_job = project.jobs.get(pipeline_job.id)
        job_as_dict = complete_job.asdict()

        for artifact in complete_job.attributes["artifacts"]:
            if artifact["file_type"] == "trace" and artifact["size"] <= trace_size_limit:
                job_as_dict["trace"] = complete_job.trace().decode("utf-8")

        collected_jobs.append(job_as_dict)

    print(f"Found {len(collected_jobs)} jobs and traces for pipeline {pipeline.id}")
    pipeline_as_dict = pipeline.asdict()
    pipeline_as_dict["jobs"] = collected_jobs
    mongo_db["pipelines"].insert_one(pipeline_as_dict)
