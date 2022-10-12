import abc
import datetime
import json

import gitlab
import os
import tempfile
import time

from abc import ABC
from elasticsearch import Elasticsearch
from pymongo import MongoClient
from typing import Dict


def get_time(latest, offset: int = 0):
    latest = latest.replace("Z", "+00:00")
    return datetime.datetime.fromisoformat(latest) + datetime.timedelta(seconds=offset)


class Sink(ABC):

    @abc.abstractmethod
    def sink(self, document: Dict, doc_type: str):
        pass

    @abc.abstractmethod
    def already_added(self, document: Dict, doc_type: str) -> bool:
        pass

    @abc.abstractmethod
    def date_of_latest_document(self, doc_type: str, date_field_name: str = "finished_at"):
        pass


class MongoDbSink(Sink):

    def __init__(self, host: str = "localhost", port: int = 27017, db_name: str = "gitlab"):
        self.mongo_client = MongoClient(f'mongodb://{host}:{port}/')
        self.mongo_db = mongo_client[db_name]

    def sink(self, document: Dict, doc_type: str):
        mongo_db[doc_type].insert_one(document)

    def already_added(self, document: Dict, doc_type: str) -> bool:
        return self.mongo_db["jobs"].find_one({"id": document["id"]}) is not None

    def date_of_latest_document(self, doc_type: str, date_field_name: str = "finished_at"):
        # db.jobs.find({ "finished_at": { $ne: null } }).sort({finished_at:-1}).limit(1)
        latest = self.mongo_db["jobs"].find(filter={date_field_name: {"$ne": "null"}},
                                            sort=[(date_field_name, -1)], limit=1,
                                            projection=[date_field_name]).next()
        if latest:
            return get_time(latest[date_field_name])
        return None


class ElasticSink(Sink):

    def date_of_latest_document(self, doc_type: str, date_field_name: str = "finished_at"):
        result = self.es_client.search(index=doc_type, query={"match_all": {}},
                                       sort=[{date_field_name: {"order": "desc"}}], size=1)
        hits = result.body["hits"]["hits"]
        if hits:
            return get_time(hits[0]["_source"][date_field_name])
        return None

    def __init__(self, host: str = "localhost", port: int = 9200):
        self.es_client = Elasticsearch(f"http://{host}:{port}")

    def sink(self, document: Dict, doc_type: str):
        self.es_client.index(index=doc_type, document=document)

    def already_added(self, document: Dict, doc_type: str) -> bool:
        hits = \
            self.es_client.search(index=doc_type, query={"term": {"id": document["id"]}})["hits"][
                "total"]["value"]
        return hits > 0


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

    def __init__(self, trace_size_limit: int, sinks: [Sink]):
        self.trace_size_limit = trace_size_limit
        self.sinks = sinks
        self.finished_after = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(
            weeks=1)
        self.determine_latest_job_date()

    def process(self, project):
        new_jobs = 0
        for pipeline in project.pipelines.list(updated_after=self.finished_after, get_all=True):
            for pipeline_job in pipeline.jobs.list(get_all=True):
                if pipeline_job.finished_at and get_time(
                        pipeline_job.finished_at) > self.finished_after:
                    job = project.jobs.get(pipeline_job.id)
                    self.output_job_and_trace(job)
                    new_jobs += 1

        print(f"Added {new_jobs} new jobs for project \"{project.name}\"")

    def determine_latest_job_date(self):
        for sink in self.sinks:
            latest_date_from_sink = sink.date_of_latest_document("jobs", "finished_at")
            if latest_date_from_sink and latest_date_from_sink > self.finished_after:
                self.finished_after = latest_date_from_sink

    def output_job_and_trace(self, job):
        job_as_dict = job.asdict()
        if self.trace_exists_and_does_not_exceed_size_limit(job):
            job_as_dict = self.add_trace(job_as_dict, job)

        for sink in self.sinks:
            document = job_as_dict.copy()
            if not sink.already_added(document, "jobs"):
                sink.sink(document, "jobs")

    def add_trace(self, job_as_dict, job):
        job_as_dict["trace"] = job.trace().decode("utf-8")
        return job_as_dict

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


def get_latest_job_date_per_project(mongo_db):
    # db.jobs.aggregate([ { $group: { _id: "$pipeline.project_id", latests: { $max: "$pipeline.updated_at" } } }])
    result = {}
    for record in mongo_db["jobs"].aggregate(pipeline=[
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
    mongo_db = mongo_client['gitlab']
    # latest_job_per_project = get_latest_job_date_per_project(mongo_db)

    stdout_sink = type('StdOutSink', (Sink, object), {"sink": lambda document, doc_type: print(
        json.dumps(document, indent=2)),
                                                      "already_added": lambda document, doc_type:
                                                      False})

    get_jobs_and_traces = GetJobsAndTraces(trace_size_limit=10000,
                                           sinks=[stdout_sink, MongoDbSink(), ElasticSink()])
    repository_exporter = ExportRepository(repository_size_limit=1000000)

    gl = gitlab.Gitlab(url='https://gitlab.com', private_token=os.getenv("GITLAB_TOKEN"))
    traverse_all_projects_in_group(os.getenv("GITLAB_GROUP_ID"), processors=[get_jobs_and_traces])
