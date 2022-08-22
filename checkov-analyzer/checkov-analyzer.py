import glob
import json
import os
import sys


def analyze_report(report):

    if report["summary"]["passed"] <= 0:
        print(f"\033[91m\U00002716 report does not contain any passed checks\033[0m")
        sys.exit(1)

    error = False

    if report["summary"]["failed"] != 0:
        print(f"\033[93m\U000026A0 report contains failed checks, checking excemptions\033[0m")

        configured_excemptions = {}

        if os.path.exists(f"{os.path.dirname(__file__)}/excemptions.json"):
            with open(f"{os.path.dirname(__file__)}/excemptions.json") as excemptions_file:
                configured_excemptions = json.load(excemptions_file)

        for failed_check in report["results"]["failed_checks"]:
            file_path = failed_check["file_path"][1:]
            check_id = failed_check["check_id"]

            if file_path not in configured_excemptions.keys():
                print(f"\033[91m\U00002716 no excemptions configured for file {file_path}\033[0m")
                error = True
                continue
            if check_id not in configured_excemptions[file_path]:
                print(f"\033[91m\U00002716 check {check_id} is not an excemption for file {file_path}\033[0m")
                error = True

    if report["summary"]["resource_count"] == 0:
        print(f"\033[91m\U00002716 no resources where checked\033[0m")
        sys.exit(1)

    manifest_dir = sys.argv[2]
    manifests = []

    for file in glob.glob("*.yaml", root_dir=manifest_dir):
        file_path = f"{manifest_dir}/{file}"
        file_size = os.path.getsize(file_path)

        print(f"checking file {file_path}")

        if os.path.getsize(file_path) <= 0:
            print(f"\033[91m\U00002716 file {file_path} either does not exist or is empty\033[0m")
            error = True
        else:
            print(f"\033[92m\U00002714 file {file_path} exits with size {file_size}b\033[0m")
            manifests.append(file_path)

    if not manifests:
        print(f"\033[91m\U00002716 no manifests found in folder {manifest_dir}\033[0m")
        sys.exit(1)

    passed_checks_for_manifest = {}
    for manifest in manifests:
        passed_checks_for_manifest[manifest] = 0

    for passed_check in report["results"]["passed_checks"]:
        file_abs_path = passed_check["file_abs_path"]
        if file_abs_path in passed_checks_for_manifest.keys():
            passed_checks_for_manifest[file_abs_path] = passed_checks_for_manifest[file_abs_path] + 1

    for file in passed_checks_for_manifest:
        passed_checks = passed_checks_for_manifest[file]
        if passed_checks == 0:
            print(f"\033[91m\U00002716 file {file} did not pass any checks\033[0m")
            error = True
        else:
            print(f"\033[92m\U00002714 file {file} passed {passed_checks} checks\033[0m")

    if error:
        print(f"\033[1;91m\n\U00002716 scan report contains errors (see above)\033[0m")
        sys.exit(1)
    else:
        print(f"\033[1;92m\n\U00002714 scan report does not contain any errors\033[0m")
        sys.exit(0)


if __name__ == '__main__':

    with open(sys.argv[1], 'r') as report_file:
        reports = json.load(report_file)

    if type(reports) == list:
        for report in reports:
            analyze_report(report)
    else:
        analyze_report(reports)