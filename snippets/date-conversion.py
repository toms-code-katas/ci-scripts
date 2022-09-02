import datetime

if __name__ == '__main__':
    date = datetime.datetime(year=2020, month=2, day=29, hour=10, minute=53, second=21, microsecond=345000,
                             tzinfo=datetime.timezone(offset=datetime.timedelta(hours=2)))
    print(date.isoformat(sep="T", timespec='milliseconds'))
    # Format in mongo db: 2022-08-31T13:20:37.529Z

    datetime.fromisoformat("2022-08-31T13:22:21.136+00:00")
