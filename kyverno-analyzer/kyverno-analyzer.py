import re
import sys
import yaml

# To remove the first lines of the report which are not yaml use:
# tail -n +7 policy-report.yaml > policy-report-without-header.yaml
if __name__ == '__main__':

    ignore_errors = {"prometheus-pushgateway-liveness-and-readiness-probes-are-required": [
        r"validation error",
        r"Liveness and readiness probes are required",
        "release-name-prometheus-pushgateway"]}
    expected_errors = 1

    with open(sys.argv[1], 'r') as handle:
        collect = False
        message = ""
        errors_found = 0
        for event in yaml.parse(handle):
            if isinstance(event, yaml.MappingStartEvent):
                collect = True
            elif isinstance(event, yaml.MappingEndEvent):
                collect = False
                for error in ignore_errors:
                    all_matches_found = True
                    for pattern in ignore_errors[error]:
                        if not re.search(pattern, message):
                            all_matches_found = False
                            break
                    if all_matches_found:
                        print(f"message {message} matches ignore pattern {error}")
                        errors_found += 1
                        break
                message = ""
            elif collect:
                if hasattr(event, "value"):
                    message = message + event.value + "\n"
        if not errors_found == expected_errors:
            print(f"Expected {expected_errors} errors. Found {errors_found}")
            exit(1)