{{- define "fun-dags.name" -}}
{{- default .Chart.Name .Values.nameOverride }}
{{- end }}

{{/*
Define Selector Labels
*/}}
{{- define "fun-dags.selectorLabels" -}}
app.kubernetes.io/name: {{ include "fun-dags.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "fun-dags.labels" -}}
{{ include "fun-dags.selectorLabels" -}}
{{- end }}