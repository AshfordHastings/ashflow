from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def my_task():
    print("Hello from Cool DAG!")

dag = DAG(
    'my_cool_dag',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1)
)

task = PythonOperator(
    task_id='say_hello',
    python_callable=my_task,
    dag=dag
)

if __name__ == "__main__":
    dag.test()