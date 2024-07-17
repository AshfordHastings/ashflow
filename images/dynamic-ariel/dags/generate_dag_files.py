import json 
import os 
import shutil 
import fileinput 
from jinja2 import Template 
from capabilities import AzureBlob
from typing import Union

#from dags import dag_template
#import dag_template

config_filepath = "config/"
dag_template_path = "dag_template.py"
    
caps = {
    "ArielAFR": "ArielAFR",
    "ArielASI": "ArielASI"
}


def get_artifact_from_vault(artifact_ref: Union[str, dict], vault:dict):
    """
    Example:
    {
        "source": "AzureBlob",
        "params": {
            "blob_path: "path_to_blob"
        }
    }
    """

    if type(artifact_ref) is str:
        return f"""{artifact_ref}"""

    artifact_spec = vault[artifact_ref['valueFrom']['artifactRef']]

    if artifact_spec["source"] == "AzureBlob":
        return f"""AzureBlob(
            blob_path="{artifact_spec["params"]["blob_path"]}"
        )"""
    else:
        raise Exception(f'Type for {artifact_spec["source"]} not found.')


def parse_stages(stages:dict, vault:dict):
    for stage_name, stage in stages.items():
        for input_name, input_spec in stage.get('input').items():
            artifact = get_artifact_from_vault(input_spec, vault)
            #Update dict
            stages[stage_name]['input'][input_name] = artifact
        for output_name, output_spec in stage.get('output').items():
            artifact = get_artifact_from_vault(output_spec, vault)
            #Update dict
            stages[stage_name]['output'][output_name] = artifact
    return stages

def generate_dag(config:dict, template:str):
    template = Template(template)
    dag_code = template.render(
        capabilities=caps,
        dag_id=config['dag_id'],
        schedule=config['schedule'],
        stages=parse_stages(config['stages'], config['artifacts']),
        chain=config['chain']
    )
    return dag_code

def generate_dags():
    for filename in os.listdir(config_filepath):
        f = open(config_filepath + filename)
        config = json.load(f)

        # Create a new DAG file to be registered by DAGBAG with unique ID
        dag_filepath = "generated/" + config["dag_id"] + ".py"
        #shutil.copyfile(dag_template_path, new_filename)

        f = open(dag_template_path)
        template = f.read()

        generated_dag = generate_dag(config, template)
        print(generated_dag)
        with open(dag_filepath, 'w') as f:
            f.write(generated_dag)

if __name__ == "__main__":
    generate_dags()
        


