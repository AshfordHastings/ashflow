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

{{- define "standard_airflow_environment" }}
- name: AIRFLOW__CORE__LOAD_EXAMPLES
  value: "False"
- name: AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION
  value: "True"
- name: AIRFLOW__WEBSERVER__WEB_SERVER_URL_PREFIX
  value: /
- name: AIRFLOW__WEBSERVER__BASE_URL
  value: http://airflow.local
- name: AIRFLOW__WEBSERVER__WEB_SERVER_BASE_URL
  value: http://airflow.local
- name: AIRFLOW__CORE__FERNET_KEY
  valueFrom:
    secretKeyRef:
      key: fernet-key
      name: ashflow-fernet-key
- name: AIRFLOW_HOME
  value: /opt/airflow
- name: AIRFLOW__CORE__SQL_ALCHEMY_CONN
  valueFrom:
    secretKeyRef:
      key: connection
      name: ashflow-metadata
- name: AIRFLOW__DATABASE__SQL_ALCHEMY_CONN
  valueFrom:
    secretKeyRef:
      key: connection
      name: ashflow-metadata
- name: AIRFLOW_CONN_AIRFLOW_DB
  valueFrom:
    secretKeyRef:
      key: connection
      name: ashflow-metadata
- name: AIRFLOW__WEBSERVER__SECRET_KEY
  valueFrom:
    secretKeyRef:
      key: webserver-secret-key
      name: ashflow-webserver-secret-key
{{- end }}