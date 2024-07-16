import json 
import os 
import shutil 
import fileinput 
from jinja2 import Template 

from dags import dag_template

config_filepath = "config/"
dag_template_path = "dag-template.py"

def _ArielAFR():
    print("Running ArielAFR!")

def _ArielASI(): 
    print("Running ArielASI!")

capabilities = {
    "ArielAFR": _ArielAFR,
    "ArielASI": _ArielASI
}

def generate_dag(config:dict, template:str):
    template = Template(template)
    dag_code = template.render(
        capabilities=capabilities,
        dag_id=config['dag_id'],
        schedule=config['schedule'],
        stages=config['stages'],
        chain=config['chain']
    )
    return dag_code

for filename in os.listdir(config_filepath):
    f = open(config_filepath + filename)
    config = json.load(f)

    # Create a new DAG file to be registered by DAGBAG with unique ID
    new_filename = "generated/" + config["dag_id"] + ".py"
    shutil.copyfile(dag_template_path, new_filename)

    f = open(dag_template_path)
    template = f.read()

    generated_dag = generate_dag(config, template)
    with open(dag_template_path, 'w') as f:
        f.write(generated_dag)
    


