import sys
from kubernetes import client, config, utils

def mem_fmt(num, suffix="Gi"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


class DeploymentResourcesCalculator:

    def __init__(self, apps_v1_api, autoscaling_v1_api, namespace, deployment):
        self.apps_v1_api = apps_v1_api
        self.autoscaling_v1_api = autoscaling_v1_api
        self.namespace = namespace
        self.deployment = deployment
        self.deployment_name = deployment.metadata.name

    def get_deployment(self):
        return self.apps_v1_api.read_namespaced_deployment(self.deployment_name, self.namespace)

    def get_horizontal_pod_autoscaler(self):
        for hpa in self.get_all_horizontal_pod_autoscalers().items:
            scale_target_ref = hpa.spec.scale_target_ref
            if self.matches_deployment(scale_target_ref):
                print(f"Found HPA {hpa.metadata.name} for deployment {self.deployment_name}")
                return hpa
        return None

    def get_max_replicas_from_hpa(self):
        hpa = self.get_horizontal_pod_autoscaler()
        if hpa is None:
            return None
        return hpa.spec.max_replicas

    def matches_deployment(self, scale_target_ref):
        return scale_target_ref.kind == "Deployment" and scale_target_ref.name == self.deployment_name

    def get_all_horizontal_pod_autoscalers(self):
        return self.autoscaling_v1_api.list_namespaced_horizontal_pod_autoscaler(self.namespace)

    def get_deployment_replicas(self):
        return self.deployment.spec.replicas

    def get_limits_for_all_containers(self, resource_type):
        resource_limits = []
        for container in self.deployment.spec.template.spec.containers:
            if container.resources is not None and container.resources.limits is not None:
                print(f"Found {resource_type} limit {container.resources.limits[resource_type]} for container {container.name}")
                resource_limits.append(container.resources.limits.get(resource_type))
        return resource_limits

    def calculate_total_limit(self, resource_type):
        resource_limits = self.get_limits_for_all_containers(resource_type)
        if len(resource_limits) == 0:
            return None
        total_limit = 0
        for limit in resource_limits:
            total_limit = total_limit + utils.quantity.parse_quantity(limit)
        print(f"Limit for resource {resource_type} for all containers in deployment {self.deployment_name} is {total_limit}")

        max_replicas = self.deployment.spec.replicas
        if not max_replicas or max_replicas < 0.1:
            print(f"Deployment {self.deployment_name} has no replicas set, using 1")
            max_replicas = 1
        else:
            print(f"Deployment {self.deployment_name} has {max_replicas} replicas configured")

        max_replicas_from_hpa = self.get_max_replicas_from_hpa()
        if max_replicas_from_hpa is not None:
            print(f"HPA for deployment {self.deployment_name} has {max_replicas_from_hpa} max replicas configured")
            total_limit = total_limit * max_replicas_from_hpa
        else:
            total_limit = total_limit * max_replicas

        print(f"Maximum resource consumption for resource {resource_type} for deployment {self.deployment_name} is {total_limit}")

        return total_limit




# Configs can be set in Configuration class directly or using helper utility
config.load_kube_config(sys.argv[1])

apps_client = client.AppsV1Api()
auto_scaling_client = client.AutoscalingV1Api()

deployments = apps_client.list_namespaced_deployment(sys.argv[2], watch=False)

max_cpu_consumption = 0
max_memory_consumption = 0
for deployment in deployments.items:
    print(f"Calculating limits for deployment {deployment.metadata.name}")
    calculator = DeploymentResourcesCalculator(apps_client, auto_scaling_client, sys.argv[2], deployment)
    max_cpu_consumption += calculator.calculate_total_limit("cpu")
    max_memory_consumption += calculator.calculate_total_limit("memory")

# Format memory to Gi
max_memory_consumption = max_memory_consumption / 1024 / 1024 / 1024

print(f"Maximum CPU consumption for all deployments in namespace {sys.argv[2]} is {max_cpu_consumption} cores")
print(f"Maximum memory consumption for all deployments in namespace {sys.argv[2]} is {mem_fmt(max_memory_consumption)}")
