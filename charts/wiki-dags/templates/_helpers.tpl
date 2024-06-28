{{- define "wiki-dags.name" -}}
{{- default .Chart.Name .Values.nameOverride }}
{{- end }}

{{/*
Define Selector Labels
*/}}
{{- define "wiki-dags.selectorLabels" -}}
app.kubernetes.io/name: {{ include "wiki-dags.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "wiki-dags.labels" -}}
{{ include "wiki-dags.selectorLabels" -}}
{{- end }}