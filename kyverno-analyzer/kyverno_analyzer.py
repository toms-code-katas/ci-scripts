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


class Analyzer:

    def __init__(self, config, report_path):
        self.config = config
        self.report_path = report_path
        self.result = Result()
        self.collect = False
        self.current_message = ""

    def analyze(self):
        with open(self.report_path, 'r') as handle:
            for event in yaml.parse(handle):
                if isinstance(event, yaml.MappingStartEvent):
                    self.collect = True
                elif isinstance(event, yaml.MappingEndEvent):
                    self.analyze_current_message()
                    self.current_message = ""
                elif self.collect:
                    if hasattr(event, "value"):
                        self.current_message = self.current_message + event.value + " "

        if not self.result.matches_config(self.config):
            print(f"Expected errors do not match found errors")
            return False

    def analyze_current_message(self):
        self.collect = False
        for error_to_ignore in self.config.ignore_errors:
            all_matches_found = True
            for pattern in error_to_ignore["patterns"]:
                if not re.search(pattern, self.current_message):
                    all_matches_found = False
                    break
            if all_matches_found:
                print(f"message: \"{self.current_message}\" matches ignore pattern \"{error_to_ignore['name']}\"")
                self.result.add_ignored_error(error_to_ignore["name"])
                return


def get_config(path_to_config_file):
    with open(path_to_config_file) as f:
        # use safe_load instead load
        config_map = yaml.safe_load(f)
        return Config(**config_map)


# To remove the first lines of the report which are not yaml use:
# tail -n +7 policy-report.yaml > policy-report-without-header.yaml
if __name__ == '__main__':

    cfg = get_config(sys.argv[2])

    analyzer = Analyzer(cfg, sys.argv[1])
    if not analyzer.analyze():
        exit(1)
    exit(0)
