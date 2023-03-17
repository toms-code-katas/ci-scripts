import json
import logging
import os
import time

from kubernetes import client, config, watch

class JsonFormatter(logging.Formatter):
    def format(self, record):
        message = record.msg
        if isinstance(record.msg, dict):
            message = record.msg
        else:
            message = record.getMessage()
        log_record = {
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S%z', time.gmtime()),
            'level': record.levelname,
            'message': message,
        }
        return json.dumps(log_record)


logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# Configs can be set in Configuration class directly or using helper utility
if "KUBECONFIG" in os.environ:
    logger.info(f"Using kubeconfig file from KUBECONFIG environment variable: {os.environ['KUBECONFIG']}")
    config.load_kube_config(os.environ["KUBECONFIG"])
else:
    logger.info("Using in-cluster configuration")
    config.load_incluster_config()

v1 = client.CoreV1Api()

w = watch.Watch()
wait_time = 5
while True:
    try:
        for event in w.stream(v1.list_event_for_all_namespaces):
            event_json = client.ApiClient().sanitize_for_serialization(event)
            logger.info(event_json)
    except Exception as e:
        # Log the error in json format
        logger.error(e)
        logger.info("Restarting watch in %s seconds", wait_time)
        time.sleep(wait_time)

