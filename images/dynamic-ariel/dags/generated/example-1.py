from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
from dags.capabilities import AzureBlob, ArielAFR, ArielASI

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'example-1',
    default_args=default_args,
    description='Generated DAG from config',
    schedule_interval='@daily',
)



afr_1 = PythonOperator(
    task_id='afr_1',
    python_callable=ArielAFR,
    provide_context=True,
    params={
        
        "document": AzureBlob(
            blob_path="path/to/blob"
        ),
        
        "model_id": prebuilt-document,
        
        
        "output_document": AzureBlob(
            blob_path="path/to/output/blob"
        ),
        
    },
    dag=dag,
)


asi_1 = PythonOperator(
    task_id='asi_1',
    python_callable=ArielASI,
    provide_context=True,
    params={
        
        "document": AzureBlob(
            blob_path="path/to/output/blob"
        ),
        
        "recipe_id": 1234-5678,
        
        
        "output_document": AzureBlob(
            blob_path="path/to/output/asi/blob"
        ),
        
    },
    dag=dag,
)


# Chain tasks

afr_1 >> asi_1
