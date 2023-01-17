# This script contains functions for calculating the time difference between two
# timestamps in a log file.
import json
import re
import sys
from datetime import datetime


def calculate_time_diff(last_line, second_line):
    # Both lines are in json format, so we need to extract the timestamp from the
    # "asctime" field. The timestamps are expected to be in the format
    # "2023-01-17 00:00:05,419".
    last_line_timestamp_as_string = json.loads(last_line)["asctime"]
    # Convert the timestamp to a datetime object.
    last_line_as_datetime = datetime.strptime(last_line_timestamp_as_string, "%Y-%m-%d %H:%M:%S,%f")
    second_line_timestamp_as_string = json.loads(second_line)["asctime"]
    second_line_as_datetime = datetime.strptime(second_line_timestamp_as_string, "%Y-%m-%d %H:%M:%S,%f")
    return second_line_as_datetime - last_line_as_datetime


if __name__ == '__main__':

    if len(sys.argv) != 3:
        print('Usage: time-diff.py <log-file-path> <message-regex>')
        sys.exit(1)

    log_file_path = sys.argv[1]
    message_regex = sys.argv[2]
    all_time_diffs = []

    # Iterate over all lines in the log file and find the first line that matches
    # the message regex. Then, find the next line and calculate the time difference
    # between the two lines.
    with open(log_file_path, 'r') as log_file:
        last_line = None
        for line in log_file:
            if re.search(message_regex, line):
                first_line = line
                time_diff = calculate_time_diff(last_line, first_line)
                all_time_diffs.append(time_diff)
            last_line = line

    # Sort the time differences in descending order.
    all_time_diffs.sort(reverse=True)

    # Only print the top 20 time differences.
    for time_diff in all_time_diffs[:20]:
        print(time_diff)

    # Calculate the sum of all time differences and display it as a timedelta.
    sum_of_time_diffs = sum(all_time_diffs, datetime.min)
    print(f'Sum of time differences: {sum_of_time_diffs}')
