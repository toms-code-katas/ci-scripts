import logging
import os
import sys
import time
import urllib3
import kubernetes.config as config
import kubernetes.client as client


logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)
urllib3.disable_warnings()


def log_green(msg):
    logger.info(f"\033[1;92m\U00002714 {msg}\033[0m")

def log_cyan(msg):
    logger.info(f"\033[1;36m{msg}\033[0m")

def log_yellow(msg):
    logger.info(f"\033[1;33m{msg}\033[0m")

def log_red(msg):
    logger.info(f"\033[1;31m\U0000274C {msg}\033[0m")



if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: wait-for-reconciliation-success <release-name> <namespace> <version>")
        sys.exit(1)

    # Check whether the kubec config environment variable is set and load the config file
    if "KUBECONFIG" in os.environ:
        logger.info("Using kubeconfig file from KUBECONFIG environment variable: %s", os.environ["KUBECONFIG"])
        config.load_kube_config(os.environ["KUBECONFIG"])
    else:
        logger.info("Using in-cluster configuration")
        config.load_incluster_config()

    log_green("Kubernetes config loaded successfully")

    # Get the helm release custom resource from the namespace
    release_name = sys.argv[1]
    namespace = sys.argv[2]
    version = sys.argv[3]

    CustomObjectsApi = client.CustomObjectsApi()
    helm_release = CustomObjectsApi.get_namespaced_custom_object(group="helm.toolkit.fluxcd.io", version="v2beta1", namespace=namespace, plural="helmreleases", name=release_name)

    if not helm_release:
        log_red(f"Could not find HelmRelease {release_name} in namespace {namespace}")
        sys.exit(1)

    log_green(f"Found HelmRelease {release_name} in namespace {namespace}")

    # Wait until the helm release status is true and the lastAppliedRevision is the same as the current revision
    start_time = time.time()
    while True:
        # Stop after 2 minutes waiting
        if time.time() - start_time > 120:
            log_red(f"HelmRelease {release_name} in namespace {namespace} is not in a ready state after 2 minutes")
            sys.exit(1)

        helm_release = CustomObjectsApi.get_namespaced_custom_object(group="helm.toolkit.fluxcd.io", version="v2beta1", namespace=namespace, plural="helmreleases", name=release_name)
        status = helm_release["status"]
        if status["conditions"][0]["status"] == "True" and status["lastAppliedRevision"] == version:
            log_green(f"HelmRelease {release_name} in namespace {namespace} is in a ready state")
            break
        else:
            log_yellow(f"HelmRelease {release_name} in namespace {namespace} is not in a ready state. Waiting...")
            time.sleep(5)

    log_green(f"HelmRelease reconciliation {release_name}, {version} in namespace {namespace} was successful")
    sys.exit(0)