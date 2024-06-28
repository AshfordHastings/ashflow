import logging

from pendulum import datetime
from datetime import timedelta
from airflow import DAG
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import pandas as pd

dag = DAG(
    dag_id='aggregate_wiki',
    start_date=datetime(2024, 6, 18),
    schedule_interval=timedelta(days=1),
    max_active_runs=1,
    tags=["wiki-dags"]
)

wait_for_hourly_wiki_read_completion = ExternalTaskSensor(
    task_id="wait_for_hourly_wiki_read_completion",
    external_dag_id="read_wiki_py",
    external_task_id=None,
    mode='reschedule',
    exponential_backoff=True,
    poke_interval=timedelta(minutes=1),
    max_wait=timedelta(minutes=15),
    timeout=timedelta(hours=3),
    execution_delta=timedelta(hours=0),
    dag=dag
)

def _fetch_and_aggregate_page_views(data_interval_start, data_interval_end):
    query = f"""
    SELECT pagename, SUM(pageviewcount) as daily_views
    FROM pageview_counts
    WHERE datetime >= '{data_interval_start}' AND datetime < '{data_interval_end}'
    GROUP BY pagename;
    """

    logging.info(f"Executing query: {query}")

    pg_hook = PostgresHook(postgres_conn_id='wiki_db')
    engine = pg_hook.get_sqlalchemy_engine()

    with engine.connect() as connection:
        result = connection.execute(query)
        rows = result.fetchall()

    df = pd.DataFrame(rows, columns=['pagename', 'dailyviews'])

    logging.info(f"Aggregated Data\n{df}")

    insert_query = """
    INSERT INTO daily_pageview_counts (pagename, dailyviews, date)
    VALUES (%s, %s, %s)
    """
    
    start_date = data_interval_start.date()

    data_to_insert = [
        (row['pagename'], row['dailyviews'], start_date)
        for index, row in df.iterrows()
    ]

    with engine.connect() as conn:
        conn.execute(insert_query, data_to_insert)


fetch_and_aggregate_page_views = PythonOperator(
    task_id="fetch_and_aggregate_page_views",
    python_callable=_fetch_and_aggregate_page_views,
    dag=dag,
)

wait_for_hourly_wiki_read_completion >> fetch_and_aggregate_page_views


