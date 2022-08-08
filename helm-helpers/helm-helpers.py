import argparse
from dataclasses import dataclass
import json
import glob
import os
import re
import shutil
import subprocess
from typing import Dict
import yaml


REPO_URL_MAPPING = {}


def to_string(obj):
    return obj.__class__.__name__ + "/" + obj.name


def find(element, dictionary):
    current_dictionary = dictionary
    for key in element.split('/'):
        if re.search(r'[\d+]', key):
            key = int(re.search(r'\d+', key).group())
        elif key not in current_dictionary.keys():
            return None
        current_dictionary = current_dictionary[key]
    return current_dictionary


@dataclass
class FluxObject:
    name: str = None

    def __str__(self):
        return to_string(self)

    def __hash__(self):
        return hash(self.__str__())


@dataclass
class Repository(FluxObject):
    name: str = None
    url: str = None


@dataclass
class GitRepository(Repository):
    tag: str = None


@dataclass
class HelmRepository(Repository):
    pass


@dataclass
class HelmConfigValues(FluxObject):
    values: str = None


@dataclass
class HelmRelease(FluxObject):
    chart: str = None
    repo: GitRepository = None
    repo_name: str = None
    values: HelmConfigValues = None
    values_config_map_name: str = None


def build_git_repository(yaml_block) -> GitRepository:
    repo = GitRepository(name=find("metadata/name", yaml_block), url=find("spec/url", yaml_block))
    repo.tag = get_git_repository_tag(yaml_block)
    return repo


def get_substitute_url(helm_repo_name: str) -> str:
    global REPO_URL_MAPPING
    if not REPO_URL_MAPPING:
        with open(f"{os.path.dirname(__file__)}/helm_repo_url_mapping.json") as json_file:
            REPO_URL_MAPPING = json.load(json_file)
    return REPO_URL_MAPPING[helm_repo_name]


def build_helm_repository(yaml_block) -> GitRepository:
    name: str = find("metadata/name", yaml_block)
    url: str = find("spec/url", yaml_block)
    substitute_url = get_substitute_url(name)
    if substitute_url:
        url = substitute_url
    repo = HelmRepository(name=name, url=url)
    return repo


def get_git_repository_tag(yaml_block) -> str:
    if "tag" in (ref := find("spec/ref", yaml_block)):
        return ref['tag']
    return ref['branch']


def build_helm_release(yaml_block) -> HelmRelease:
    hr = HelmRelease(name=find("metadata/name", yaml_block), chart=find("spec/chart/spec/chart", yaml_block),
                     repo_name=find("spec/chart/spec/sourceRef/name", yaml_block),
                     values_config_map_name=find("spec/valuesFrom/[0]/name", yaml_block))
    if "values" in yaml_block["spec"]:
        hr.values = HelmConfigValues(find("metadata/name", yaml_block), yaml.dump(find("spec/values", yaml_block)))
    return hr


def build_helm_values(yaml_block) -> HelmConfigValues | None:
    if "values.yaml" not in yaml_block["data"]:
        return None
    return HelmConfigValues(find("metadata/name", yaml_block), find("data/values.yaml", yaml_block))


Kind2Builder = {"GitRepository": build_git_repository, "HelmRepository": build_helm_repository,
                "HelmRelease": build_helm_release, "ConfigMap": build_helm_values}


def create_flux_objects_from_files(glob_pattern) -> Dict[str, object]:
    created_objects = {}
    for file in glob.glob(glob_pattern, recursive=True):
        with open(file, 'r') as file_stream:
            yaml_docs = yaml.load_all(file_stream, Loader=yaml.FullLoader)
            create_flux_objects_from_yaml_doc(created_objects, yaml_docs)
    return created_objects


def create_flux_objects_from_yaml_doc(created_objects, yaml_docs):
    for yaml_doc in yaml_docs:
        if not (kind := find("kind", yaml_doc)):
            print(f"Could not determine kind from {yaml_doc!s:200.200}...")
        elif kind not in Kind2Builder.keys():
            print(f"Could not find builder for kind {kind} in {yaml_doc!s:200.200}...")
        else:
            create_flux_object_from_yaml_doc(created_objects, kind, yaml_doc)


def create_flux_object_from_yaml_doc(created_objects, kind, yaml_doc):
    builder = Kind2Builder[kind]
    if not (flux_object := builder(yaml_doc)):
        print(f"Could not build flux object from {yaml_doc!s:200.200}...")
    else:
        created_objects[str(flux_object)] = flux_object


def compose_helm_releases(flux_objects):
    for release in {name: flux_object for name, flux_object in flux_objects.items() if
                    isinstance(flux_object, HelmRelease)}.values():  # type: HelmRelease
        try:
            release.repo = flux_objects[GitRepository.__name__ + "/" + release.repo_name]
        except KeyError:
            pass

        try:
            release.repo = flux_objects[HelmRepository.__name__ + "/" + release.repo_name]
        except KeyError:
            pass

        assert release.repo, f"Could not find repository with name {release.repo_name}"

        if not release.values:
            release.values = flux_objects[HelmConfigValues.__name__ + "/" + release.values_config_map_name]
        yield release


def get_chart_dependency_repos(path_to_chart: str):
    helm_chart = None
    with open(f'{path_to_chart}/Chart.yaml', 'r') as chart_file:
        helm_chart = yaml.load(chart_file, Loader=yaml.FullLoader)
    dependencies = find("dependencies", helm_chart)
    if dependencies:
        for dependency in dependencies:
            if "repository" in dependency:
                yield dependency["name"], dependency["repository"]


def add_chart_repositories(repo_list) -> bool:
    at_least_one_repo = False
    for repo in repo_list:
        subprocess.run(['helm', 'repo', 'add', repo[0], repo[1]], check=True)
        at_least_one_repo = True
    return at_least_one_repo


def build_chart_dependencies(path_to_chart):
    subprocess.run(['helm', 'dependency', 'build', path_to_chart], check=True)


def parse_args():
    parser = argparse.ArgumentParser(description='Render k8s manifests from flux helm releases')
    parser.add_argument('--base-dir', '-b', nargs='?', dest="base_path", required=True,
                        help='Path to folder containing the flux manifests')
    parser.add_argument('--work-dir', '-w', nargs='?', dest="work_dir", required=True, help='Path to working directory')

    arguments = parser.parse_args()
    return arguments


def recreate_folder(folder):
    try:
        shutil.rmtree(folder)
    except FileNotFoundError:
        pass
    os.mkdir(folder)


if __name__ == '__main__':
    args = parse_args()

    base_path = args.base_path
    working_folder = args.work_dir
    output_folder = working_folder + "/generated"

    all_flux_objects = create_flux_objects_from_files(f"{base_path}/**/*.yaml")

    recreate_folder(working_folder)
    os.mkdir(output_folder)

    for helm_release in compose_helm_releases(all_flux_objects):
        target_folder = f"{working_folder}/{helm_release.repo.name}"
        if type(helm_release.repo) is GitRepository:
            subprocess.run(['git', 'clone', '--depth', '1', '--branch', helm_release.repo.tag, helm_release.repo.url,
                        target_folder], check=True)
        else:
            add_chart_repositories([(helm_release.repo.name, helm_release.repo.url)])
            subprocess.run(['helm', 'pull', '--untar', '--untardir', target_folder, f"{helm_release.repo.name}/{helm_release.chart}"], check=True)

        release_value_file_name = f'{working_folder}/{helm_release.name}-values.yaml'
        with open(release_value_file_name, 'w') as value_file:
            value_file.write(helm_release.values.values)

        path_to_chart = target_folder + "/" + helm_release.chart

        if add_chart_repositories(get_chart_dependency_repos(path_to_chart)):
            build_chart_dependencies(path_to_chart)

        generated_manifests_file = output_folder + "/" + helm_release.name + ".yaml"
        with open(generated_manifests_file, "w") as helm_output:
            subprocess.run(['helm', '-f', release_value_file_name, 'template', '--debug', path_to_chart],
                           stdout=helm_output, check=True)

        assert os.path.exists(generated_manifests_file)
        assert os.path.getsize(generated_manifests_file) > 100
