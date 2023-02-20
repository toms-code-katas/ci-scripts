{{/*
Expand the name of the chart.
*/}}
{{- define "render-network-policy.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "render-network-policy.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "render-network-policy.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "render-network-policy.labels" -}}
helm.sh/chart: {{ include "render-network-policy.chart" . }}
{{ include "render-network-policy.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "render-network-policy.selectorLabels" -}}
app.kubernetes.io/name: {{ include "render-network-policy.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "render-network-policy.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "render-network-policy.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "render-network-policy.render" -}}
---
# Iterate over policy definitions
{{- range  $component, $component_nwp :=.policy_definition }}

apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: 
  name: {{ $component }}-network-policy
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: {{ $component }}
  policyTypes:
  - Ingress
  - Egress
{{- range $nwp_type, $nwp_blocks := . }}
{{- if eq $nwp_type "egress" }}
  egress:
{{- range $nwp_block := $nwp_blocks }}
{{- include "render-network-policy.render-block" $nwp_block | nindent 4 }}
{{- end }}
{{- else if eq $nwp_type "ingress" }}
  ingress: null
{{ end }}
{{- end }}

{{- end }}

{{- end }}

{{- define "render-network-policy.render-block" -}}
{{- if hasKey . "ipBlocks" }}
{{- range $ipBlock := get . "ipBlocks" -}}
from:
- ipBlock:
    cidr: {{ get $ipBlock "cidr" }}
ports:
- port: {{ get $ipBlock "port" }}
protocol:  {{ get $ipBlock "protocol" }}
{{- end }}
{{- end }}
{{- end }}