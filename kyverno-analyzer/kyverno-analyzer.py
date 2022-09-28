import re
import sys
import yaml


class Config:
    def __init__(self, **entries):
        self.__dict__.update(entries)


def get_config(path_to_config_file):
    with open(path_to_config_file) as f:
        # use safe_load instead load
        config_map = yaml.safe_load(f)
        return Config(**config_map)


# To remove the first lines of the report which are not yaml use:
# tail -n +7 policy-report.yaml > policy-report-without-header.yaml
if __name__ == '__main__':

    config = get_config(sys.argv[2])

    with open(sys.argv[1], 'r') as handle:
        collect = False
        message = ""
        errors_found = 0
        for event in yaml.parse(handle):
            if isinstance(event, yaml.MappingStartEvent):
                collect = True
            elif isinstance(event, yaml.MappingEndEvent):
                collect = False
                for to_ignore in config.ignore_errors:
                    all_matches_found = True
                    for pattern in to_ignore["patterns"]:
                        if not re.search(pattern, message):
                            all_matches_found = False
                            break
                    if all_matches_found:
                        print(f"message {message} matches ignore pattern {to_ignore['name']}")
                        errors_found += 1
                        break
                message = ""
            elif collect:
                if hasattr(event, "value"):
                    message = message + event.value + "\n"
        if not errors_found == expected_errors:
            print(f"Expected {config.expected_errors} errors. Found {errors_found}")
            exit(1)
