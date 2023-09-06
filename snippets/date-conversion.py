import datetime

if __name__ == '__main__':
    date = datetime.datetime(year=2020, month=2, day=29, hour=10, minute=53, second=21, microsecond=345000,
                             tzinfo=datetime.timezone(offset=datetime.timedelta(hours=2)))
    print(date.isoformat(sep="T", timespec='milliseconds'))
    # Format in mongo db: 2022-08-31T13:20:37.529Z

    print(date.utcnow())

    print(date.strptime("2022-10-04T13:45:37", "%Y-%m-%dT%H:%M:%S"))
    # date.strptime("2022-10-04T13:45:37.028", "%Y-%m-%dT%H:%M:%S.sss")
    print(date.strptime("2022-10-04T13:45:37.028Z", "%Y-%m-%dT%H:%M:%S.%fZ"))
    # date.fromisoformat("2022-08-31T13:22:21.136+00:00")
    # date.fromisoformat('2022-10-04T13:45:37.028Z')

