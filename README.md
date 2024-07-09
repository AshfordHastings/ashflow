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




### Global / Local Execution Configurations and Limits
#### Global Configurations
- **AIRFLOW__CORE__MAX_ACTIVE_RUNS_PER_DAG**
	- The maximum number of active DAG runs per DAG. The scheduler will not create more DAG runs if it reaches the limit. This is configurable at the DAG level with `max_active_runs`, which is defaulted as `[core] max_active_runs_per_dag`.
	- Current Setting: "30"
- **AIRFLOW__CORE__MAX_ACTIVE_TASKS_PER_DAG**
	- Max Active tasks per DAG (for ALL DAG runs combined)
	- Current Setting: "30"
- **AIRFLOW__CORE__MAX_CONSECUTIVE_FAILED_DAG_RUNS_PER_DAG**
	- The maximum number of consecutive DAG failures before DAG is automatically paused. This is also configurable per DAG level with `max_consecutive_failed_dag_runs`, which is defaulted as `[core] max_consecutive_failed_dag_runs_per_dag`. If not specified, then the value is considered as 0, meaning that the dags are never paused out by default.
	- Current Setting: "10"
- **AIRFLOW__CORE__PARALLELISM**
	- This defines the maximum number of task instances that can run concurrently per scheduler in Airflow, regardless of the worker count. Generally this value, multiplied by the number of schedulers in your cluster, is the maximum number of task instances with the running state in the metadata database.
	- Current Setting: "32"
- **AIRFLOW__SCHEDULER__MIN_FILE_PROCESS_INTERVAL**
	- Number of seconds after which a DAG file is parsed. The DAG file is parsed every `[scheduler] min_file_process_interval` number of seconds. Updates to DAGs are reflected after this interval. Keeping this number low will increase CPU usage. This is the interval at which the scheduler should try to process a file (not new files, just updated files)
	- Current Setting: "30"
- **AIRFLOW__SCHEDULER__DAG_DIR_LIST_INTERVAL**
	- The interval that the scheduler looks for NEW dags in seconds - safe to set to 30 seconds for less than 200 DAGs
	- Current Setting: "30"
- **AIRFLOW__KUBERNETES__WORKER_PODS_CREATION_BATCH_SIZE**
	- How many pods can be created per scheduler loop
	- Current Setting: "4"
	- 
**Other Configurations**
- **AIRFLOW__KUBERNETES__DELETE_WORKER_PODS_ON_FAILURE**
	- If False (and delete_worker_pods is True), failed worker pods will not be deleted so users can investigate them.
	- Current Setting: "False"
- **AIRFLOW__CORE__MAX_MAP_LENGTH
	- The maximum list/dict length an XCom can push to trigger task mapping. If the pushed list/dict has a length exceeding this value, the task pushing the XCom will be failed automatically to prevent the mapped tasks from clogging the scheduler.
	- Current Setting: 1024

#### Execution Strategy
There are a number of configurations in Airflow controlling, for example, the execution of Tasks within in a DAG, such as number of Tasks per DAG, the number of Tasks globally, the number of active DAG runs per DAG, number of active tasks in a Task Pool (different than Postgres Connection pooling), etc. 

Some of these configurations are set globally, but apply to the individual DAG level, such as  `AIRFLOW__CORE__MAX_ACTIVE_TASKS_PER_DAG`, which will prevent active tasks in a DAG from exceeding a certain number. The reaching of this limit is not affected whatsoever by the execution of other DAGs for other application teams, or other DAGs. For configurations such as these, it may be safe to apply a high global threshold to prevent DAGs from accidentally going haywire, but this is not a necessity, and potentially should be left in the DAG authors hands.

Other configurations such as `AIRFLOW__CORE__PARALLELISM` are affected by other DAGs, and if implemented, would rely on other configurations to limit DAGs from hogging slots. For example, a DAG authored by Application Team A, who may be less familiar with some of the standards in DAG authoring, creates a Sensor to retrieve files from an SMB drive, with the Sensor using its `execution_date` to query the suffixes of file names to evaluate their presence. However, the Sensor is set to `poke`,  the `start_date` is set to four days ago, the schedule interval is every hour, and the `timeout` for the Sensor is infinite. And, as it turns out, SMB files are only placed in the drive during a three hour window in the afternoon. What would happen is that upon launching the DAG, there would be `three days x 21 hours` DAG runs executed, with their sensors continuously running. That would be 63 active Tasks at once, reaching the global `AIRFLOW__CORE__PARALLELISM` default threshold of 32 active task instances. Now, if Application Team B attempts to deploy their DAGs, none of their DAGs would even be scheduled! 

Now, the most obvious solution is to turn all of these thresholds off, and scale the schedulers. The justification for having these global limitations on DAG Runs, active Tasks, etc is to prevent resource overallocation to certain DAGs, which may affect others by overconsumption on the node in which the Tasks are being executed. This would be important when using `LocalExecutor`, because resource hungry DAGs running many Tasks could crash the scheduler, and for `CeleryExecutor`, there are still a static number of nodes executing workloads. When using `KubernetesExecutor`, however, the tasks for every DAG are run on isolated Pods, and these Pods, in turn, are run on respective application team namespaces, which will have ResourceQuotas assigned to them at the namespace scope. If the number of active tasks, in this circumstance, corresponds to the number of Pods, then the Object Count Quota for the namespace would be able to successfully limit the number of active Tasks for a specific application team, with DAG specific applied at the DAG level.

There are a number of unknowns here that will be investigated in other sections: if the Scheduler attempts to schedule a Sensor on a DAG's namespace, but the Object Count quota is exceeded, will the Task be marked as Queued, Failed, or Running (where it will take up a Execution Slot)? Either way -  for our initial implementation, we should most likely not be setting global configurations, due to the inability to alter these configurations to individual application teams, and due to the possibility of one application team running DAGs that affect the ability of other teams to schedule their own Tasks. Understanding resource usage at the Kubernetes cluster level should be done first and foremost, with strategies for monitoring, testing, and setting limitations. 

It is also worth noting that the third category of some of these configurations, such as `AIRFLOW__CORE__MAX_CONSECUTIVE_FAILED_DAG_RUNS_PER_DAG`, are overridable by individual DAG. For this, the concern should be to make the lives of DAG authors easier by setting reasonable defaults, and thinking about the manner they perform deployments and the potential issues they will run into during the learning process. 

#### Task Pooling 

### Node Pooling

#### Initial Strategy

There are different strategies that we could implement for running Airflow on AKS. We could either have a separate node pool for core Airflow components, and use other nodes for the Kubernetes Jobs that arise, or we could have all components run on their own node pool. 

Assigning workloads to nodes works by adding "taints" to a node to prevent pods from being assigned to a node unless they have a specific "toloration" added. On the Pods, you can either add tolerations that can override these taints, or you can have nodeSelectors on the pods. 

Things like HPA are not going to matter as much here - since pods are spun up on the fly. If we decide to put all resources on the same node pool, our strategy needs to assure that scheduler, web server, etc pods and their replicas are able to evict running tasks (preemption policies) and will not be evicted by a queued node. If all Airflow tasks are running on the same pool, and KubernetesExecutor is used, I am assuming that the Task would go into a "queued" state while waiting for resources to become avaliable. If the Node runs out of resources, the pod will either get throttled if it is CPU, or OOMMemory if Memory - and Task would go into failed. For resource requesting strategy - 

An example of how we would apply tolerations is using 
`kubectl taint nodes <airflow node pool> dedicated=airflow:NoSchedule`. "NoSchedule" means that any pods without a matching toleration cannot be scheduled to this node pool. Adding a toleration to a pod would look like:
```yaml
tolerations:
- key: "key1"
  operator: "Equal"
  value: "value1"
  effect: "NoSchedule"
OR 
tolerations:
- key: "key1"
  operator: "Exists"
  effect: "NoSchedule"
```
The "NoSchedule" directive is absolute. If a pod has `spec.nodeName` configured to a node, but doesn't have this toleration, the kubelet will eject this pod after scheduling. Additionally, an empty key toleration with operator Exists will tolerate everything and get scheduled to any node. NoExecute will affect pods running ON the node and evict them - NoSchedule will not schedule new pods. PreferNoSchedule will *try* not to schedule the new pods. 

Airflow workloads will be unique and highly variable. A Pod is created and executed for every single task - some tasks will use few resources, some will have high resource usages. There are times where no dags will be ran, but then, there are times when a very high number of tasks will be ran at the same time. It is better to have a task be "queued" than a task die during its execution, and it is the worst to have the scheduler, etc die. A DAGs PodTemplateFile will set a base resource requests and limits - but different tasks will have different requirements for resource utilization. If a Task is in BestEffort, nothing will stop it from being placed on a node and hitting the upper bound. If it is guaranteed, it would be necessary to have the resources the task use best match its resource requests, for the sake of the node not running out, not being able to schedule more pods, queueing them, performance. 

The most likely strategy to go with is having all core airflow components be of Guaranteed. This is to assure their ability to stay up. Tasks, however, are variable - so it is best that Airflow Tasks receive a baseline, and have a higher resource limit so that pods can continuously be scheduled, even if the requests are lower. We do want to prevent a bunch of failing tasks for resource reasons, however. When in doubt, set limits high rather than low. Start high, and use monitoring tools to survey the actual consumption. 

Other side is that, if you set a limit really high, and a request really low, the scheduler will be fine putting that Task on a node with barely any resources left. So maybe keep them as close as possible at the start. What we SHOULD do is add in custom executor configs and provide them to asks, and instruct people to add these to their task definition so that tasks can easily be customized as high resource and low resource utilization.  

#### Node Pool Sizing
Which VMs to use? 
Core components:
 - 1 Standard_D8as_v5 node
 - 1 x 32Gib memory = 32 Gib
 - 1 x 8 vCPU = 8 vCPU
 - Total Memory:
	 - 2 Scheduler Replicas x 4Gi(limit) = 8 Gi
	 - 2 Web Server Replicas x 2Gi(limit) = 4 Gi
	 - 12 Total (so far)
- Total CPU:
	- 2 Sch x 2CPU = 4 CPU
	- 2 Web x 1CPU = 2 CPU
	- 6 CPU total (so far)
- Cost:
	- $0.376 per Hour x 24 x 30 = $270 a month per node 
DAG Tasks:
-  2 Standard_D8as_v5 node
- 2 x 32Gib memory = 64 Gib
- 2 x 8 vCPU = 16 vCPU
- Pod Template:
	- CPU r/l: .5CPU / .5CPU
	- Memory: r/l: 1 GB/ 1 GB
- How many Tasks can be ran? 
	- Remember - Nodes will stop scheduling not at 100, but before that. There are also control plane components that get scheduled to nodes in addition (like Aqua, kubeproxy, etc). These need to be understood. 
	- 16 vCPU / .5CPU per Task = Less than 32 Tasks Run in Parallel. 
	- 64 GB / 1 GB per Task = Less than 64 Tasks Run in Parallel. 
	- Seems fine for the initial run. 
*Necessary idea for administration of Airflow: Enforcement of maximum ratio of 1.5 between request / limit for PodTemplateFiles*

#### Resource Monitoring 
It is important to use the


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
