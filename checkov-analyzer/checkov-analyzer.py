import glob
import json
import os
import sys


if __name__ == '__main__':
    with open(sys.argv[1], 'r') as report_file:
        report = json.load(report_file)

    assert report["summary"]["passed"] > 0
    assert report["summary"]["failed"] == 0
    assert report["summary"]["resource_count"] > 0

    error = False
    manifest_dir = sys.argv[2]
    manifests = []
    for file in glob.glob("*.yaml", root_dir=manifest_dir):
        file_path = f"{manifest_dir}/{file}"
        file_size = os.path.getsize(file_path)

        try:
            assert os.path.getsize(file_path) > 0
        except AssertionError:
            print(f"\033[91m\U00002716 file {file_path} either does not exist or is empty")
            error = True
        else:
            print(f"\033[92m\U00002714 file {file_path} exits with size {file_size}b")
            manifests.append(file_path)

    passed_checks_for_manifest = {}
    for manifest in manifests:
        passed_checks_for_manifest[manifest] = 0

    for passed_check in report["results"]["passed_checks"]:
        file_abs_path = passed_check["file_abs_path"]
        if file_abs_path in passed_checks_for_manifest.keys():
            passed_checks_for_manifest[file_abs_path] = passed_checks_for_manifest[file_abs_path] + 1
        else:
            print(f"\033[91m\U00002716 file {file_abs_path} in report was not part of generated manifests")
            error = True

    for file in passed_checks_for_manifest:
        passed_checks = passed_checks_for_manifest[file]
        if passed_checks == 0:
            print(f"\033[91m\U00002716 file {file} did not pass any checks")
            error = True
        else:
            print(f"\033[92m\U00002714 file {file} passed {passed_checks} checks")