import re
import sys
import yaml


class Config:
    def __init__(self, **entries):
        self.__dict__.update(entries)


class Result:

    def __init__(self):
        self.errors_ignored = {}

    def add_ignored_error(self, name):
        if name in self.errors_ignored:
            self.errors_ignored[name] = self.errors_ignored[name] + 1
        else:
            self.errors_ignored[name] = 1

    def matches_config(self, config):
        matches = True
        for to_ignore in config.ignore_errors:
            error_name = to_ignore["name"]
            if error_name not in self.errors_ignored:
                print(f"Expected error {error_name} not found")
                matches = False
            elif self.errors_ignored[error_name] != to_ignore["expected_errors"]:
                print(f"Expected {to_ignore['expected_errors']} occurrences of error \"{error_name}\""
                      f" found {self.errors_ignored[error_name]} occurrences")
                matches = False
        return matches


def get_config(path_to_config_file):
    with open(path_to_config_file) as f:
        # use safe_load instead load
        config_map = yaml.safe_load(f)
        return Config(**config_map)


# To remove the first lines of the report which are not yaml use:
# tail -n +7 policy-report.yaml > policy-report-without-header.yaml
if __name__ == '__main__':

    config = get_config(sys.argv[2])
    result = Result()

    with open(sys.argv[1], 'r') as handle:
        collect = False
        message = ""
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
                        print(f"message: \"{message}\" matches ignore pattern \"{to_ignore['name']}\"")
                        result.add_ignored_error(to_ignore["name"])
                        break
                message = ""
            elif collect:
                if hasattr(event, "value"):
                    message = message + event.value + " "

    if not result.matches_config(config):
        print(f"Expected errors do not match found errors")
        exit(1)
