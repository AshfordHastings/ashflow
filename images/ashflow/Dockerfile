FROM apache/airflow:2.8.3
USER root 

# Install apt packages

USER airflow

COPY requirements.txt /
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements.txt 
