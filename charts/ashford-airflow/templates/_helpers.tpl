{{- define "ashflow.name" -}}
{{- default .Chart.Name .Values.nameOverride }}
{{- end }}

{{/*
Define Selector Labels
*/}}
{{- define "ashflow.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ashflow.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "ashflow.labels" -}}
{{ include "ashflow.selectorLabels" -}}
{{- end }}