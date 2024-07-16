from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
from helpers import {{ capability }}

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
def {{ stage_id }}_task(**kwargs):
    {{ capabilities['stage.capability'] }}(
        document=kwargs['params']['document'],
        {% if 'model_id' in stage.input %}model_id=kwargs['params']['model_id'], {% endif %}
        {% if 'recipe_id' in stage.input %}recipe_id=kwargs['params']['recipe_id'], {% endif %}
    )

{{ stage_id }} = PythonOperator(
    task_id='{{ stage_id }}',
    python_callable={{ stage_id }}_task,
    provide_context=True,
    params={
        'document': {{ stage.input.document }},
        {% if 'model_id' in stage.input %}'model_id': {{ stage.input.model_id }}, {% endif %}
        {% if 'recipe_id' in stage.input %}'recipe_id': {{ stage.input.recipe_id }}, {% endif %}
    },
    dag=dag,
)
{% endfor %}

# Chain tasks
{% for chain in chain %}
{{ chain }}
{% endfor %}