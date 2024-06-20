from airflow.utils.dates import days_ago
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.operators.postgres import SQLExecuteQueryOperator
# from airflow.providers.http.sensors.http import HttpSensor
from airflow.sensors.python import PythonSensor
from pendulum import datetime
from datetime import timedelta 
from urllib import request
import json
import logging


dag = DAG(
    dag_id='read_wiki_py',
    start_date=days_ago(1),
    schedule_interval='@hourly',
    max_active_runs=12,
    template_searchpath="/tmp" # Default WORKDIR of where Operators search for files
)

def _check_data_avaliability(year, month, day, hour):
    url = (
        "https://dumps.wikimedia.org/other/pageviews/"
        f"{year}/{year}-{month}/pageviews-{year}{month}{day}-{hour}0000.gz"
    )
    logging.info(f"Making request to ${url}.")
    try:
        request.urlopen(url)
        logging.info("Data is avaliable. Proceeding.")
        return True
    except:
        logging.info("Data is unavaliable. Rescheduling.")
        return False
    
check_data = PythonSensor(
    task_id="wait_for_data",
    python_callable=_check_data_avaliability,
    op_kwargs={
        "year": "{{ execution_date.year }}",
        "month": "{{ '{:02}'.format(execution_date.month) }}",
        "day": "{{ '{:02}'.format(execution_date.day) }}",
        "hour": "{{ '{:02}'.format(execution_date.hour) }}",
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

    output_path = f"/tmp/wikipageviews_{year}{month}{day}-{hour}.gz"
    logging.info(f"Making request to ${url} and writing to ${output_path}.")

    request.urlretrieve(url, output_path)

    ti.xcom_push(key="output_path", value=output_path)


get_data = PythonOperator(
    task_id="get_data",
    python_callable=_get_data,
    op_kwargs={
        "year": "{{ execution_date.year }}",
        "month": "{{ '{:02}'.format(execution_date.month) }}",
        "day": "{{ '{:02}'.format(execution_date.day) }}",
        "hour": "{{ '{:02}'.format(execution_date.hour) }}",
    },
    dag=dag,
)

extract_data = BashOperator(
    task_id="extract_data",
    bash_command=(
        "gunzip --force {{ ti.xcom_pull(task_ids='get_data', key='output_path') }}"
    ),
    dag=dag,
)

def _fetch_pageviews(pagenames, execution_date, ti):
    output_path = ti.xcom_pull(task_ids='get_data', key='output_path')
    page_views = {pagename: 0 for pagename in pagenames}
    with open(output_path.replace('.gz', ''), 'r') as f:
        for line in f:
            domain_code, page_title, view_counts, _ = line.split(" ")
            if domain_code == "en" and page_title in pagenames:
                page_views[page_title] = view_counts
    logging.info(f"PAGE VIEWS: {json.dumps(page_views, indent=2)}")

    query_file = f"postgres_query{output_path.split('_')[1].replace('.gz', '.sql')}"
    with open(f"/tmp/{query_file}", "w") as f:
        for page_name, view_count in page_views.items():
            f.write(
                "INSERT INTO pageview_counts VALUES ("
                f"'{page_name}', '{view_count}', '{execution_date}'"
                ");\n"
            )
    logging.info(f"Writing SQL script to ${query_file}.")
    ti.xcom_push(key='query_file', value=query_file)


fetch_pageviews = PythonOperator(
    task_id="fetch_pageviews",
    python_callable=_fetch_pageviews,
    op_kwargs={
        "pagenames": ["Facebook", "Amazon", "Apple", "Netflix", "Google"]
    },
    dag=dag
)

write_to_postgres = SQLExecuteQueryOperator(
    task_id="write_to_postgres",
    sql="/tmp/{{ ti.xcom_pull(task_ids='fetch_pageviews', key='query_file') }}", # This itself is a template - so it is going to assume it is just sql
    conn_id="wiki_db"
)

check_data >> get_data >> extract_data >> fetch_pageviews >> write_to_postgres



"""
wiki

https://dumps.wikimedia.org/other/pageviews/{year}/
{year}-{month}/pageviews-{year}{month}{day}-{hour}0000.gz

"""

