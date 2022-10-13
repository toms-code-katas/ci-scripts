import abc
import datetime
import json

import gitlab
import logging
import os
import sys
import tempfile
import time

from abc import ABC
from elasticsearch import Elasticsearch
from pymongo import MongoClient
from typing import Dict

logging.basicConfig(
    level=logging.DEBUG,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s",'
           ' "function": "%(funcName)s:%(lineno)d", "message": "%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger('gitlab-issue-exporter')
logging.getLogger('urllib3').setLevel("WARNING")
logging.getLogger('elastic_transport').setLevel("WARNING")


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

    def date_of_latest_document(self, doc_type: str, date_field_name: str = "created_at"):
        return datetime.datetime.now(tz=datetime.timezone.utc)


class MongoDbSink(Sink):

    def __init__(self, host: str = "localhost", port: int = 27017, db_name: str = "gitlab"):
        self.mongo_client = MongoClient(f'mongodb://{host}:{port}/')
        self.mongo_db = mongo_client[db_name]

    def sink(self, document: Dict, doc_type: str):
        mongo_db[doc_type].insert_one(document)

    def already_added(self, document: Dict, doc_type: str) -> bool:
        found_document = self.mongo_db[doc_type].find_one({"id": document["id"]})
        if not found_document:
            logger.debug(
                f"No document found with id \"{document['id']}\" in collection \"{doc_type}\"")
            return False
        else:
            logger.debug(
                f"Document found with id \"{document['id']}\" already added"
                f" to collection \"{doc_type}\"")
            return True

    def date_of_latest_document(self, doc_type: str, date_field_name: str = "created_at"):
        # db.jobs.find({ "created_at": { $ne: null } }).sort({created_at:-1}).limit(1)
        latest = next(self.mongo_db["jobs"].find(filter={date_field_name: {"$ne": "null"}},
                                                 sort=[(date_field_name, -1)], limit=1,
                                                 projection=[date_field_name]), None)
        if latest:
            logger.debug(f"Latest \"{date_field_name}\" value is {latest[date_field_name]}")
            return get_time(latest[date_field_name])
        else:
            logger.debug(
                f"No value for field \"{date_field_name}\" found in collection \"{doc_type}\"")
            return None


class ElasticSink(Sink):

    def date_of_latest_document(self, doc_type: str, date_field_name: str = "created_at"):
        result = self.es_client.search(index=doc_type, query={"match_all": {}},
                                       sort=[{date_field_name: {"order": "desc"}}], size=1)
        hits = result.body["hits"]["hits"]
        if hits:
            latest = hits[0]["_source"][date_field_name]
            logger.debug(f"Latest \"{date_field_name}\" value is {latest}")
            return get_time(latest)
        else:
            logger.debug(
                f"No value for field \"{date_field_name}\" found in index \"{doc_type}\"")
            return None

    def __init__(self, host: str = "localhost", port: int = 9200):
        self.es_client = Elasticsearch(f"http://{host}:{port}")

    def sink(self, document: Dict, doc_type: str):
        self.es_client.index(index=doc_type, document=document)

    def already_added(self, document: Dict, doc_type: str) -> bool:
        hits = \
            self.es_client.search(index=doc_type, query={"term": {"id": document["id"]}})["hits"][
                "total"]["value"]
        already_added = hits > 0
        if already_added:
            logger.debug(
                f"Document found with id \"{document['id']}\" already added"
                f" to index \"{doc_type}\"")
        else:
            logger.debug(f"No document found with id \"{document['id']}\" in index \"{doc_type}\"")

        return already_added


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
        self.created_after = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(
            weeks=1)
        self.determine_latest_job_date()

    def process(self, project):
        jobs_found = 0
        for pipeline in project.pipelines.list(updated_after=self.created_after, get_all=True):
            for pipeline_job in pipeline.jobs.list(get_all=True):
                if pipeline_job.created_at and get_time(
                        pipeline_job.created_at) > self.created_after:
                    job = project.jobs.get(pipeline_job.id)
                    self.output_job_and_trace(job)
                    jobs_found += 1

        logger.debug(f"Found {jobs_found} jobs for project \"{project.name}\"")

    def determine_latest_job_date(self):
        latest_date_from_sinks = []
        for sink in self.sinks:
            latest_date_from_sinks.append(sink.date_of_latest_document("jobs", "created_at"))

        applicable_date = None
        for latest_date in latest_date_from_sinks:
            if not latest_date:
                logger.debug("At least one sink did not provided a latest job date, using default")
                applicable_date = self.created_after
                break
            elif not applicable_date:
                applicable_date = latest_date
            elif latest_date < applicable_date:
                applicable_date = latest_date

        logger.debug(f"Determined latest job date to {applicable_date}")
        self.created_after = applicable_date

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
                                           sinks=[MongoDbSink(), ElasticSink()])
    repository_exporter = ExportRepository(repository_size_limit=1000000)

    gl = gitlab.Gitlab(url='https://gitlab.com', private_token=os.getenv("GITLAB_TOKEN"))
    traverse_all_projects_in_group(os.getenv("GITLAB_GROUP_ID"), processors=[get_jobs_and_traces])
