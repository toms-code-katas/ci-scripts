# This script deletes old pipelines from a GitLab project including all
# related artifacts and jobs.
# The time for which the pipelines are kept can be configured by using
# the --keep-time argument. Which takes the time in the format of 10d or 2w etc.
# It is intended to be run as a cron job.
# It requires the GitLab API token to be set in the environment variable
# GITLAB_API_TOKEN.

import argparse
import datetime
import gitlab

def parse_args():
    parser = argparse.ArgumentParser(description='Delete old pipelines from a GitLab project.')
    parser.add_argument('--project', required=True, help='The project ID or path of the project')
    parser.add_argument('--keep-time', default='365d', help='The time for which the pipelines are kept')
    parser.add_argument('--dry-run', action='store_true', help='Do not delete anything, just print what would be deleted')
    parser.add_argument('--url', required=True, default='https://gitlab.com', help='The url of the GitLab instance')
    parser.add_argument('--token', required=True, help='The GitLab API token')

    return parser.parse_args()

def parse_keep_time(keep_time):
    if keep_time[-1] == 'd':
        return datetime.timedelta(days=int(keep_time[:-1]))
    elif keep_time[-1] == 'w':
        return datetime.timedelta(weeks=int(keep_time[:-1]))
    elif keep_time[-1] == 'm':
        return datetime.timedelta(days=int(keep_time[:-1]) * 30)
    elif keep_time[-1] == 'y':
        return datetime.timedelta(days=int(keep_time[:-1]) * 365)
    else:
        raise ValueError('Invalid time format')

def main():
    args = parse_args()
    keep_time = parse_keep_time(args.keep_time)
    gl = gitlab.Gitlab(args.url, args.token)
    project = gl.projects.get(args.project)

    # jobs = project.jobs.list(order_by="finished_at", sort='asc', per_page=100, all=True)
    # for job in jobs:
    #     print(job.finished_at)

    # Convert the keep_time to a datetime object and format it to the ISO 8601 format
    updated_before = (datetime.datetime.now(datetime.timezone.utc) - keep_time).isoformat()

    # Print the date for which we are deleting pipelines
    print(f'Deleting pipelines finished before {updated_before}')

    pipelines = project.pipelines.list(updated_before=updated_before, sort='asc', per_page=100, all=True)
    for pipeline in pipelines:
        if pipeline.status == 'running':
            continue

        current_utc_time = datetime.datetime.now(datetime.timezone.utc)
        pipeline_updated_at = pipeline.updated_at

        # To convert the pipeline_updated_at to a datetime object we need to
        # use the correct pattern for the ISO 8601 format
        time_pipeline_updated = datetime.datetime.strptime(pipeline_updated_at, '%Y-%m-%dT%H:%M:%S.%fZ')

        # In order to calculate the time diff we need to convert the time to the same time zone
        time_pipeline_updated = time_pipeline_updated.replace(tzinfo=datetime.timezone.utc)
        # Now we can calculate the time diff
        time_diff = current_utc_time - time_pipeline_updated

        # Print the time diff in days
        print(f'Pipeline {pipeline.id} finished {time_diff.days} days ago')

        # Compare time zones to make sure we are comparing the same time
        if time_diff > keep_time:

            jobs = pipeline.jobs.list(all=True)
            for pipeline_job in jobs:
                job = project.jobs.get(pipeline_job.id, lazy=False)
                job.delete_artifacts()

            print(f'Deleting pipeline {pipeline.id} finished at {pipeline_updated_at}')
            pipeline.delete()
            print(f'Successfully deleted pipeline {pipeline.id}')


if __name__ == '__main__':
    main()