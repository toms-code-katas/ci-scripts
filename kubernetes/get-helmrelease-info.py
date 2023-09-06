# This script is used to get the helmrelease info from all namespaces. This info includes:
# - the helmrelease name
# - the last attempted revision
# - the last applied revision
# - All status conditions with lastTransitionTime, message and reasons

import json
import logging
import os
import time

from kubernetes import client, config, watch

# This data class is used to store the helmrelease info
class HelmReleaseInfo:
    def __init__(self, namespace, name, last_attempted_revision, last_applied_revision, conditions):
        self.namespace = namespace
        self.name = name
        self.last_attempted_revision = last_attempted_revision
        self.last_applied_revision = last_applied_revision
        self.conditions = conditions


if "KUBECONFIG" in os.environ:
    config.load_kube_config(os.environ["KUBECONFIG"])
else:
    config.load_incluster_config()

custom_objects_api = client.CustomObjectsApi()

# Get the client for accessing namespaces
core_api = client.CoreV1Api()

# Get all namespaces
namespaces = core_api.list_namespace()

# Iterate over the namespaces and get all helmreleases and store them in a list
helm_release_info_list = []

for namespace in namespaces.items:
    namespace_name = namespace.metadata.name
    helm_releases = custom_objects_api.list_namespaced_custom_object(group="helm.toolkit.fluxcd.io", version="v2beta1", namespace=namespace_name, plural="helmreleases")
    for helm_release in helm_releases["items"]:
        namespace = helm_release["metadata"]["namespace"]
        name = helm_release["metadata"]["name"]
        last_attempted_revision = helm_release["status"]["lastAttemptedRevision"]
        last_applied_revision = helm_release["status"]["lastAppliedRevision"]
        conditions = helm_release["status"]["conditions"]
        helm_release_info = HelmReleaseInfo(namespace, name, last_attempted_revision, last_applied_revision, conditions)
        helm_release_info_list.append(helm_release_info)

# Now iterate over the list and print the info sorted by the conditions lastTransitionTime
for helm_release_info in sorted(helm_release_info_list, key=lambda x: x.conditions[0]["lastTransitionTime"]):
    print(f"Namespace: {helm_release_info.namespace}, Name: {helm_release_info.name}, Last attempted revision: {helm_release_info.last_attempted_revision}, Last applied revision: {helm_release_info.last_applied_revision}, Conditions: {helm_release_info.conditions}")
