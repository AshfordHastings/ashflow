# ARIEL Airflow Proposal, etc. 

## Table of Contents
1. [Components](#components)
	- [Database](#database)
	- [PGBouncer](#pgbouncer)
2. [Strategies](#strategies)
	- [Separation of DAG Processors](#Separation-of-DAG-Processors)
	- [Connection to External Systems](#Connection-to-External-Systems)
		- [Overview]()
		- [Connections to On-Prem, External Systems]()
		- [Application Teams Providing Data Platforms]
		- [Connection to Azure Services]
		- [Local Development]

## Components
### Database
Apache Airflow requires a database in which to store information such as serialized DAGs, dag runs, users, etc. In DEV2 at the moment, we are utilizing a PostgreSQL database running on a Kubernetes StatefulSet, which is created by the Apache Airflow Helm Chart. The connection to an external database for Airflow Core can be altered through the Values.yaml file for the Airflow Helm Chart, in which it takes params for an external database.

A challenge is that while the configuration, and underlying SQLAlchemy code, expects a static Connection String, this will not suffice with our method of connecting to an Azure PostgreSQL Server database using Managed Identity. In this scenario, the connection string is dynamic, as Azure AD / Entra performs a token exchange in the background which is used in the connection string. I have seen information on how to configure this, and need to understand how I would implement this.

Additionally, Apache Airflow fully expects to be in charge of its own database. Airflow uses Alembic, and for future Apache Airflow upgrades, Alembic is used for the database migration and schema updates to new versions. The database is very complex, and we would not want to handle any of this manually. Airflow must have the adequete roles to handle the database initialization and potential future migration on the metadata database source. 

### PGBouncer
Due to Airflow's distributed nature, Airflow will open up many database connections. In using KubernetesExecutor, every Airflow Task will run a Pod which will connect to the database for storing task execution data. As we've seen in the past with TXT_AAC, we need a way to limit and manage this. 

Use of PGBouncer as a connection pooler for Airflow is recommended and offered as an easy addon by the Airflow maintainers. The pooler maintains an active pool of active database connections that are able to be reused be multiple clients, without the overhead of opening and closing connections to the database. Additionally, we can tightly configure and monitor the total number of allowed connections at one time. PGBouncer does this by allowing single connections to be used by several, distributed transactions, dedicated session pooling, lowering the amount of connections required by Airflow. Configurations include maxClientConn (def 100) metadataPoolSize (max number of server connections to metadata db, def 10), result backend pool size (def 5). 

## Strategies
### Separation of DAG Processors
[Airflow Documentation - Separation of DAG File Processing](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/dagfile-processing.html)
[AIP-43 with Justification Discussion](https://cwiki.apache.org/confluence/display/AIRFLOW/AIP-43+DAG+Processor+separation)

For details, please read the brief link above. In short, the environment variable `AIRFLOW__SCHEDULER__STANDALONE_DAG_PROCESSOR=True` must be set to assure that DAG files are processed isolated from the scheduler. This can be configured in the Apache Airflow Helm Chart via `dagProcessor.*`. 

The Helm Chart allows for a series of configurations for how to run the standalone DAG processor, most importantly, `dagProcessor.command` and `dagProcessor.args`. It will default to running another dag procesor. But, there is an option to have `-S, --subdir` when executing. This will instruct the DAG processor to only process files from a certain directory. This may be necessary if we want not just to separate DAG processing from the scheduler, but to have different replicas of the DAG processor actually assigned to specific application DAG groups. This may be overengineering, however.  

The aims for what we can accomplish by separating the DAG processing component will inform much of the implementation. But requirements for the application include, *if I deploy an syntax errored DAG, will this affect other components?*. The multitenancy requirement of ARIEL Airflow can bring about questions of code injection, malicious actors, etc, but really, the most important question is, what are ways in which a DAG author would reasonable mess something up, how would it affect other components, and how can we eliminate this possibility in a way that is clear and logical? I am not sure what happens if there are syntax errors in the DAG itself, but I know for a fact that if there are syntax errors in the PodTemplateOverride, that the scheduler will fail. By separating out the DAG processor, we should confirm that deploying broken DAGs will not affect the core scheduler component. In addition, we need to make sure the DAG processor deployed is able to self heal on deployment of broken DAGs. The Helm Chart has all sort of configurations for this in the DAG processor. 

### Connection to External Systems
#### Overview
Airflow is commonly used to pull and push data into other systems, both within our Azure tenant, such as user databases, Event Hubs, etc and from outside sources, such as on-prem databases, IMS systems, Sharepoint, Kafka etc. To facilitate connection to these sources, Airflow offers various means, including *Airflow Connections*, *Airflow Variables*, and *Airflow Hooks*. 

*Airflow Connections* represent a connection string for connecting to an external source. The Connection String is stored as:
`my-conn-type://my-login:my-password@my-host:5432/my-schema?param1=val1&param2=val2` for example. Connection objects to external sources will additionally contain values that must be encrypted and secured. For example, a json representation of a Connection object would look like this: 
```
{
		"conn_id": "my_postgres_conn"
        "conn_type": "my-",
        "login": "my-login",
        "password": "my-password",
        "host": "my-host",
        "port": 1234,
        "schema": "my-schema",
        "extra": {
            "param1": "val1",
            "param2": "val2"
}
```

while a URI format would be `postgresql://user:password@hostname:5432/dbname`. An HTTP Connection would be represented like `http://username:password@servvice.com:80/https?headers=header'. 

Airflow provides DAGs with abstractions called *Hooks* that can be initialized with the ID of a connection object in its connection. Inside of a PythonOperator, one may generate a connection string through a PostgresHook, or use the PostgresHook to generate queries on the database that the Connection specifies. 

Apache Airflow also has concepts called *Variables*, which may be sensitive or not. Variables can contain either secrets requiring encryption, or non-secret application variables. Within the process of a deploying DAGs across different environments, there may be different strategies for setting and storage of these variables to give users a transparent and easy process. Hence, in lower, testing environments, it may be necessary to provide means through which secrets can be provided through the CI/CD pipeline, this would be disabled in higher environments. Application variables, on the other hand, would not have any requirement to be stored in Azure Key Vault, and should not be. 

To start, let's discuss the usage of secret Connections and Variables within Airflow. 

#### Connections to On-Prem, External Systems
There are several options for secure storage of these secret Connections / Variables:
- Storage in Metadata Database. Encryption using Fernet Key, which would be stored as a Kubernetes Secret.
- Storage in Kubernetes Secret objects. 
- Storage in *Secrets Backend*, which utlizes an external secrets store such as Azure Key Vault or HashiCorp Vault. 

When enabling an alternative secrets store, the search path that Airflow would take would be to check the alternative secrets backend, followed by environment variables (which would be set, for example, via `AIRFLOW_CONNECTIONS___MY_POSTGRES_CONN)`, and finally, by querying the database for Connections and Variables stored in the Metadata Database. To store a Connection/Variable in Azure Key Vault, one would prefix an Azure Key Vault Secret with the global prefix set locally in the airflow.cfg, similarly to how you would set a connection as an environment variable. In the event of key collision, Airflow will prioritize values stored in the secrets backend. 

Apache Airflow can only be configured with a single Secrets Backend at the global level. This means that not only will DAG users be forced to import their secrets to a single instance of Azure Key Vault used by all DAGs, but every DAG will have the ability to utilize the secrets from every other DAG author, provided they know the key that they stored the value as. On one hand, we do not want to prevent overengineering where unnecessary. In our current strategy for deploying application workloads to a shared Kubernetes cluster, there is no isolation of application secrets: our cluster's Secret Store CSI drive currently retrieves values from Azure Key Vault and instantiates them as Kubernetes secrets upon Helm installation, to be used inside the chart's deployment workload, but there are no Kubernetes RBAC isolation measures preventing applications from another project accessing and using these secrets. Actually, there are no isolatory measures of any kind for the most part between projects, so should the goal of isolation really be defined as app-to-app security, or as logical, developer-friendly, isolation? 

In any case, there is a potential resolution to this. The logic present in a Hook to retrieve secrets from a custom Secrets Backend is executed at the Pod level, so when a Hook is utilized in the context of a Task using KubernetesExecutor, the Hook will use the SecretsBackend specified in the PodTemplateFile. A possibility is that a PodTemplateFile can, if they want to specify a separate instance of Azure Key Vault specific to their application, they can do this. However, maybe more realistic for what we want to do, can specify a separate backend_kwarg value for their connection / variable prefix. So as that, if two applications want to store a connection called "my_postgres_db", one application would be able to prefix this in Azure Key Vault as `AIRFLOW_CONN_TEAM_A__MY_POSTGRES_DB` while the second would specify `AIRFLOW_CONN_TEAM_B__MY_POSTGRES_DB`. 

To access Azure Key Vault, an AzureIdentityBinding and AzureIdentity will be created for *Airflow Core* and have all necessary accesses to Azure Key Vault. The exact role necessary needs to be confirmed so that LPA can be respected. 

Besides secret isolation, which may be something we can put off until later, a concern to prioritize under the goal of "abstractions made simple" and "testable" is to have systems in which application teams can transparently add secrets. 

Now - we need to identify the means in which we can add secrets to Azure Key Vault, make clear all of the processes that exist, identify secrets that exist in Azure Key Vault, etc. Also - per environment. Otherwise, we're just going to be redirecting a million users to Sriram who need secrets to run their DAGs. This should be clear and documented, and we should offer ways around this in lower environments. 

#### Application Teams Providing Data Platforms
The goal of the Recon team is to implement means for LLM agents to access a number of data sources within the context of DAGs. Other use cases such as Email Classification and EZOps (EZOps solution to this issue in the beginning was to store files in an SMB drive from their end with one connection) require business clients to be able to configure the connection to a number of email drives. I am not sure of the details of some of this implementation, and I imagine some of this will be covered in sections regarding providing DAGs with custom SPNs for use cases, etc for Azure use cases. 

The assumptions above is that, a DAG deployment will consist of static secrets that will live in one place, be known upon deployment, and, for any new Secrets, require a redeployment, or at least modification of secrets in the secret store. This also conflicts with another proposal for assuring DAGs would not fail upon attempting to access non-existant secrets, which is a hook that would potentially analyze a DAG and confirm that the values referred to as secrets in Azure Key Vault actually exist.

I don't know the solution - but whatever that solution may be, it should be visible, clear, etc. If an application team has a large number of secrets for different sources, these should be put into a configuration file within the DAGs git and imported, to allow for clarity, etc, so there aren't a million secrets that get lost. Something with the goal of organization, clarify, configurability. 

#### Connection to Azure Services

To connect to an Azure Service, you have the ability to use an Azure Hook. I'm going to talk about the complexities of some of this implementation, and how this would work, but I would like to reiterate that whether it be Hooks or Operators in Airflow, these, especially, are *offerings* to make things *simpler*, not requirements, and any recommendation that is counterintuitive to our clarity, ease of use, obviousness in implementation, should be reconsidered for alternatives, such as asking users to simply user the Azure Python SDK within a PythonOperator to do what the Hooks and Operators are doing under the hood.  

In either case, in an AzureHook or manual authentication, the DAG will be, in most cases, using a Managed Identity to connect to a resource. A Managed Identity can be assigned to any Kubernetes workload using either AAD Pod Identity or Azure AD Workload ID. In the former case, AzureIdentity and AzureIdentityBinding objects must be installed to the cluster, with the AzureIdentity object provided role assignments to the target Azure resource being accessed, with the Kubernetes workload representing the principal. To instruct the (in the form auth method) AAD Pod Identity Kubernetes addon to engage in the token exchange process, the principal Pod which the Managed Identity represents must be assigned an annotation (or label, I forgot) which the AzureIdentityBinding can map to. 

If we want to give the Airflow workload the binding which the AAD Pod Identity extension can match to, does that mean that we have to redeploy all of Airflow, with every component given access to this application team's instance of Azure Blob Storage, or Data Factory, etc (additionally, annotations are immutable if I remember correctly)? That would be difficult to manage. Instead, the practice will be to have the DAG, or group of DAGs, use a PodTemplateFile containing the proper label that the AzureIdentityBinding can select, and ensure that it can use `DefaultAzureCredential` to initialize and connect to the relevent Azure Resource. This binding would be just a plain label, so it would have no environment specific features here, and can be promoted as an image normally. 

This would require the AzureIdentity and AzureIdentityBinding to be deployed separately though, and relates to the concept of performing a Helm *release* of the txt-flow-app-base Chart directly versus an application authoring their own chart, with their own Helm template files, using txt-flow-app-base as a dependency. That will be talked about more in a separate section. 

Now - in Azure, if a workload is assigned only one managed identity, the process is simple. Just use `DefaultAzureCredential` and, since you only have only Managed Identity assigned to the workload, Azure has a pretty good idea of which identity to check the roles for. If you have multiple, however, I forgot exactly what happens (maybe the one with highest privledge?), but you would typically want to provide the ID for the Managed Identity which you are attempting to use represent yourself as when making the Azure request. 

Here, we encounter a minor issue with DAGs being environment agnostic - this will most likely need to be set as a *Variable* in Airflow. Or, retrieved as an environment variable, or connecting to Kubernetes or something, I don't know. There must be a way to abstract this process from the user, or automate this to some extant. 

An important note is that the Airflow UI will only show connections and variables stored in the Metadata DB - meaning that there may be implementations in which users will not be able to validate their objects through the UI by name or the value that they represent when writing their DAGs. 
#### Local Development
- Secrets store can be set as a variable_file_path backend_kwarg and LocalFileSystemBackend and backend in the airflow.cfg. This would be useful for local development. 
