import glob
import os.path
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

    def matches_config(self, applicable_rules):
        matches = True
        for rule in applicable_rules:
            rule_name = rule["name"]
            if rule_name not in self.errors_ignored:
                print(f"\033[1;91m\U00002716 Expected match for {rule_name} not found\033[0m")
                matches = False
            elif self.errors_ignored[rule_name] != rule["expected_errors"]:
                print(f"\033[1;91m\U00002716 Expected {rule['expected_errors']} occurrences of error \"{rule_name}\""
                      f" found {self.errors_ignored[rule_name]} occurrences\033[0m")
                matches = False
            elif self.errors_ignored[rule_name] == rule["expected_errors"]:
                print(f"\033[1;92m\U00002714 Expected occurrences of error \"{rule_name}\""
                      f" match found occurrences\033[0m")
        return matches


class Analyzer:

    def __init__(self, config_path, report_path):
        self.config = self.get_config(config_path)
        self.report_path = report_path
        self.report_file_name = os.path.basename(report_path)
        self.result = Result()
        self.collect = False
        self.current_message = ""
        self.applicable_rules = []
        self.select_rules_for_report_file()

    def analyze(self):
        if not self.applicable_rules:
            return not self.has_errors()

        with open(self.report_path, 'r') as handle:
            for event in yaml.parse(handle):
                if isinstance(event, yaml.MappingStartEvent):
                    self.collect = True
                # only if rule has been added to the current message is the message complete
                elif isinstance(event, yaml.MappingEndEvent) and "rule" in self.current_message:
                    self.analyze_current_message()
                    self.current_message = ""
                elif self.collect:
                    if hasattr(event, "value"):
                        self.current_message = self.current_message + event.value + " "

        if not self.result.matches_config(self.applicable_rules):
            print(f"\033[1;91m\U00002716 Expected errors do not match errors found\033[0m")
            return False
        return True

    def has_errors(self):
        summary_element_found = False
        error_element_found = False
        number_of_errors = -1

        with open(self.report_path, 'r') as handle:
            for event in yaml.parse(handle):
                if isinstance(event, yaml.ScalarEvent):
                    if event.value == "summary":
                        summary_element_found = True
                    elif summary_element_found and event.value == "error":
                        error_element_found = True
                    elif summary_element_found and error_element_found:
                        number_of_errors = int(event.value)
                        break

        if number_of_errors == -1:
            print("\033[92m\U00002714 No summary found\033[0m")
            return True
        elif number_of_errors != 0:
            print(
                f"\033[1;91m\U00002716 Summary of report {self.report_path} contains {number_of_errors} errors."
                f" None were expected\033[0m")
            return True
        elif number_of_errors == 0:
            print(f"\033[1;92m\U00002714 No rules configured for report {self.report_path}, No errors found\033[0m")

    def analyze_current_message(self):
        self.collect = False
        for rule in self.applicable_rules:
            all_matches_found = True
            for pattern in rule["patterns"]:
                if not re.search(pattern, self.current_message):
                    all_matches_found = False
                    break

            if all_matches_found:
                print(f"\033[1;92m\U00002714 Found match for rule \"{rule['name']}\"\033[0m")
                self.result.add_ignored_error(rule["name"])
            else:
                return False

    def get_config(self, config_path):
        with open(config_path) as f:
            config_map = yaml.safe_load(f)
            return Config(**config_map)

    def select_rules_for_report_file(self):
        for rule in self.config.rules:
            if self.report_file_name in rule["files"]:
                self.applicable_rules.append(rule)


# To remove the first lines of the report which are not yaml use:
# tail -n +7 policy-report.yaml > policy-report-without-header.yaml
if __name__ == '__main__':

    error_found = False
    for report in glob.glob(sys.argv[1], recursive=True):
        print(f"Analyzing file {report}")
        analyzer = Analyzer(sys.argv[2], report)
        if not analyzer.analyze():
            error_found = True
    exit(1 if error_found else 0)
