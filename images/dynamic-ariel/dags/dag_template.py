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
    '{{ dag_id }}',
    default_args=default_args,
    description='Generated DAG from config',
    schedule_interval={{ schedule }},
)

{% for stage_id, stage in stages.items() %}

{{ stage_id }} = PythonOperator(
    task_id='{{ stage_id }}',
    python_callable={{ capabilities[stage['capability']] }},
    provide_context=True,
    params={
        {% for input_id, input_val in stage.input.items() %}
        "{{ input_id }}": {{ input_val }},
        {% endfor %}
        {% for output_id, output_val in stage.output.items() %}
        "{{ output_id }}": {{ output_val }},
        {% endfor %}
    },
    dag=dag,
)
{% endfor %}

# Chain tasks
{% for chain in chain %}
{{ chain }}
{% endfor %}