from airflow.utils.dates import days_ago
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
# from airflow.providers.postgres.operators.postgres import SQLExecuteQueryOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
# from airflow.providers.http.sensors.http import HttpSensor
from airflow.sensors.python import PythonSensor
from pendulum import datetime
from datetime import timedelta 
from urllib import request
import json
import logging
import os

from kubernetes.client import models as k8s

executor_config_template = {
    "pod_override": k8s.V1Pod(
        spec=k8s.V1PodSpec(
            containers=[
                k8s.V1Container(
                    name="base",
                    volume_mounts=[
                        k8s.V1VolumeMount(
                            mount_path="/mnt/wiki/",
                            name="wiki-volume")
                    ],
                )
            ],
            volumes=[
                k8s.V1Volume(
                    name="wiki-volume",
                    persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(claim_name="wiki-dags-com-vol")
                )
            ],
        )
    ),
}

dag = DAG(
    dag_id='read_wiki_py',
    start_date=datetime(2024, 6, 18),
    schedule_interval=timedelta(minutes=60),
    max_active_runs=10,
    template_searchpath="/mnt/wiki", # Default WORKDIR of where Operators search for files
    default_args={
        "retries": 4,
        "retry_delay": timedelta(seconds=15),
        "retry_exponential_backoff": False,
        "max_retry_delay": timedelta(minutes=1),
    },
    tags=["wiki-dags"]
) # This will execute the DAG from 12:00 3 days before current date, on hourly intervals, 



def _check_data_avaliability(year, month, day, hour):
    url = (
        "https://dumps.wikimedia.org/other/pageviews/"
        f"{year}/{year}-{month}/pageviews-{year}{month}{day}-{hour}0000.gz"
    )
    logging.info(f"Making request to ${url}.")
    try:
        request.urlopen(url)
        logging.info(f"Data is avaliable at {url}. Proceeding.")
        return True
    except:
        logging.info(f"Data is unavaliable at {url}. Rescheduling.")
        return False
    
check_data = PythonSensor(
    task_id="wait_for_data",
    python_callable=_check_data_avaliability,
    op_kwargs={
        "year": "{{ data_interval_start.year }}",
        "month": "{{ '{:02}'.format(data_interval_start.month) }}",
        "day": "{{ '{:02}'.format(data_interval_start.day) }}",
        "hour": "{{ '{:02}'.format(data_interval_start.hour) }}",
    },
    poke_interval=timedelta(minutes=30),
    timeout=timedelta(hours=3),
    mode="reschedule",
    dag=dag,
)


def _get_data(year, month, day, hour, ti ):

    url = (
        "https://dumps.wikimedia.org/other/pageviews/"
        f"{year}/{year}-{month}/pageviews-{year}{month}{day}-{hour}0000.gz"
    )

    output_path = f"/mnt/wiki/wikipageviews_{year}{month}{day}-{hour}.gz"
    logging.info(f"Making request to ${url} and writing to ${output_path}.")

    request.urlretrieve(url, output_path)

    ti.xcom_push(key="output_path", value=output_path)


get_data = PythonOperator(
    task_id="get_data",
    python_callable=_get_data,
    op_kwargs={
        "year": "{{ data_interval_start.year }}",
        "month": "{{ '{:02}'.format(data_interval_start.month) }}",
        "day": "{{ '{:02}'.format(data_interval_start.day) }}",
        "hour": "{{ '{:02}'.format(data_interval_start.hour) }}",
    },
    # executor_config={"KubernetesExecutor": executor_config_template}, # I don't think this one needs the objects and stuff? 
    executor_config=executor_config_template,
    dag=dag,
)

extract_data = BashOperator(
    task_id="extract_data",
    bash_command=(
        "gunzip --force {{ ti.xcom_pull(task_ids='get_data', key='output_path') }}"
    ),
    dag=dag,
    executor_config=executor_config_template
)

def _fetch_pageviews(pagenames, ti):
    output_path = ti.xcom_pull(task_ids='get_data', key='output_path')
    true_path = output_path.replace('.gz', '')
    page_views = {pagename: 0 for pagename in pagenames}
    with open(true_path, 'r') as f:
        for line in f:
            domain_code, page_title, view_counts, _ = line.split(" ")
            if domain_code == "en" and page_title in pagenames:
                page_views[page_title] = view_counts
    logging.info(f"PAGE VIEWS: {json.dumps(page_views, indent=2)}")

    if os.path.exists(true_path):
        os.remove(true_path)
        logging.info(f"Removed path {true_path}.")

    ti.xcom_push(key='page_views', value=page_views) # page_views is pickleable


fetch_pageviews = PythonOperator(
    task_id="fetch_pageviews",
    python_callable=_fetch_pageviews,
    op_kwargs={
        "pagenames": ["Facebook", "Amazon", "Apple", "Netflix", "Google"]
    },
    executor_config=executor_config_template,
    dag=dag
)

def _write_to_postgres(data_interval_start, ti):
    page_views = ti.xcom_pull(task_ids='fetch_pageviews', key='page_views')

    postgres_hook = PostgresHook(postgres_conn_id="wiki_db")

    for page_name, view_count in page_views.items():
        postgres_hook.run(
            "INSERT INTO pageview_counts VALUES (%s, %s, %s)",
            parameters=(page_name, view_count, data_interval_start)
        )


write_to_postgres = PythonOperator(
    task_id="write_to_postgres",
    python_callable=_write_to_postgres,
    op_kwargs={
        # 'page_views': "{{ ti.xcom_pull(task_ids='fetch_pageviews', key='page_views') }}",
        # 'execution_date': "{{ execution_date }}"
    },
    executor_config=executor_config_template,
    dag=dag
)

# write_to_postgres = SQLExecuteQueryOperator( # can use "parameters" to fill the template, but parameters itself cannot be templated, I think
#     task_id="write_to_postgres",
#     sql="/tmp/{{ ti.xcom_pull(task_ids='fetch_pageviews', key='query_file') }}", # This itself is a template - so it is going to assume it is just sql
#     conn_id="wiki_db"
# )

check_data >> get_data >> extract_data >> fetch_pageviews >> write_to_postgres



"""
wiki

https://dumps.wikimedia.org/other/pageviews/{year}/
{year}-{month}/pageviews-{year}{month}{day}-{hour}0000.gz

"""

