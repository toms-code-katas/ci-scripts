# pylint: disable=C0114,C0115,C0116

import abc
import datetime
import json
import logging
import os
import sys

from abc import ABC
from typing import Dict

import gitlab
from elasticsearch import Elasticsearch
from pymongo import MongoClient

logging.basicConfig(
    level=logging.DEBUG,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s",'
           ' "function": "%(funcName)s:%(lineno)d", "message": "%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger('gitlab-job-exporter')
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

    # pylint: disable=R0201
    def date_of_latest_document(self, doc_type: str, date_field_name: str = "created_at"):
        pass


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
                "No document found with id \"%s\" in collection \"%s\"", document['id'], doc_type)
            return False

        logger.debug(
            "Document found with id \"%s\" already added"
            " to collection \"%s\"", document['id'], doc_type)
        return True

    def date_of_latest_document(self, doc_type: str, date_field_name: str = "created_at"):
        latest = next(self.mongo_db["jobs"].find(filter={date_field_name: {"$ne": "null"}},
                                                 sort=[(date_field_name, -1)], limit=1,
                                                 projection=[date_field_name]), None)
        if latest:
            logger.debug("Latest \"%s\" value is %s", date_field_name, date_field_name)
            return get_time(latest[date_field_name])

        logger.debug(
            "No value for field \"%s\" found in collection \"%s\"", date_field_name, doc_type)
        return None


class ElasticSink(Sink):

    def date_of_latest_document(self, doc_type: str, date_field_name: str = "created_at"):
        result = self.es_client.search(index=doc_type, query={"match_all": {}},
                                       sort=[{date_field_name: {"order": "desc"}}], size=1)
        hits = result.body["hits"]["hits"]
        if hits:
            latest = hits[0]["_source"][date_field_name]
            logger.debug("Latest \"%s\" value is %s", date_field_name, latest)
            return get_time(latest)

        logger.debug(
            "No value for field \"%s\" found in index \"%s\"", date_field_name, doc_type)
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
                "Document found with id \"%s\" already added"
                " to index \"%s\"", document['id'], doc_type)
        else:
            logger.debug("No document found with id \"%s\" in index \"%s\"", document['id'],
                         doc_type)

        return already_added


# Visitor pattern
# https://refactoring.guru/design-patterns/visitor
class GetPipelineJobsAndTraces:

    def __init__(self, trace_size_limit: int, sinks: [Sink]):
        self.trace_size_limit = trace_size_limit
        self.sinks = sinks
        self.created_after = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(
            weeks=52)
        self.determine_latest_pipeline_date()

    def process(self, project):
        pipelines_found = 0
        for pipeline in project.pipelines.list(updated_after=self.created_after, get_all=True):
            if not self.is_pipeline_new(pipeline):
                continue

            pipeline_as_dict = self.convert_to_dict(pipeline)
            pipeline_jobs = pipeline.jobs.list(get_all=True)

            self.add_jobs_and_traces(pipeline_jobs, pipeline_as_dict, project)
            logger.debug(
                "Found %s jobs for pipeline "
                "\"%s\"", len(pipeline_as_dict['jobs']), pipeline_as_dict['id'])

            self.write_to_sinks(pipeline_as_dict)
            pipelines_found += 1

        logger.debug("Found %s pipelines for project %s", pipelines_found, project.name)

    def write_to_sinks(self, pipeline_as_dict):
        for sink in self.sinks:
            sink.sink(pipeline_as_dict, "pipelines")

    def add_jobs_and_traces(self, jobs, pipeline_as_dict, project):
        for pipeline_job in jobs:
            job = project.jobs.get(pipeline_job.id)
            pipeline_as_dict["jobs"].append(self.add_trace(job))

    def is_pipeline_new(self, pipeline):
        return pipeline.created_at and get_time(pipeline.created_at) > self.created_after

    @staticmethod
    def convert_to_dict(pipeline):
        pipeline_as_dict = pipeline.asdict()
        pipeline_as_dict["jobs"] = []
        return pipeline_as_dict

    def determine_latest_pipeline_date(self):
        latest_date_from_sinks = []
        for sink in self.sinks:
            latest_date_from_sinks.append(sink.date_of_latest_document("pipeline", "created_at"))

        applicable_date = None
        for latest_date in latest_date_from_sinks:
            if not latest_date:
                logger.debug("At least one sink did not provided a latest job date, using default")
                applicable_date = self.created_after
                break

            if not applicable_date:
                applicable_date = latest_date
            elif latest_date < applicable_date:
                applicable_date = latest_date

        logger.debug("Determined latest pipeline date to %s", applicable_date)
        self.created_after = applicable_date

    def add_trace(self, job):
        job_as_dict = job.asdict()
        if self.trace_exists_and_does_not_exceed_size_limit(job):
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


if __name__ == '__main__':
    mongo_client = MongoClient('mongodb://localhost:27017/')
    mongo_db = mongo_client['gitlab']

    StdoutSink = type('StdOutSink', (Sink, object), {"sink": lambda document, doc_type: print(
        json.dumps(document, indent=2)),
                                 "already_added": lambda document, doc_type:
                                 False,
                                 "date_of_latest_document": lambda doc_type,
                                                                   df_name: datetime.datetime.now(
                                     tz=datetime.timezone.utc) - datetime.timedelta(
                                     weeks=52)})

    get_jobs_and_traces = GetPipelineJobsAndTraces(trace_size_limit=10000,
                                                   sinks=[StdoutSink, MongoDbSink()])

    gl = gitlab.Gitlab(url='https://gitlab.com', private_token=os.getenv("GITLAB_TOKEN"))
    traverse_all_projects_in_group(os.getenv("GITLAB_GROUP_ID"), processors=[get_jobs_and_traces])
