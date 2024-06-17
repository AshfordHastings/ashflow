{{- define "cool-dags.name" -}}
{{- default .Chart.Name .Values.nameOverride }}
{{- end }}

{{/*
Define Selector Labels
*/}}
{{- define "cool-dags.selectorLabels" -}}
app.kubernetes.io/name: {{ include "cool-dags.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "cool-dags.labels" -}}
{{ include "cool-dags.selectorLabels" -}}
{{- end }}