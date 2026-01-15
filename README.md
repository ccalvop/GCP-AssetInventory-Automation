# GCP Asset Inventory Automation

This repository explains how to export the GCP Asset Inventory data into BigQuery. 

The export can be done **manually** using `gcloud` commands in your terminal, which is part of the Google Cloud SDK. This SDK provides command-line tools to interact with Google Cloud services and must be installed and configured on your machine to execute the commands successfully. 

Alternatively, exports can be done **automatically** using `Cloud Scheduler` and the Asset Inventory API. This automation helps monitor and analyze assets in your GCP environment which can be useful for tracking resources across projects or organizations.

<p align="center">
<img src="https://github.com/user-attachments/assets/d6026cc3-1953-462d-b216-244f0602f186" />
</p>

## Manual Export

### Step 1: Set the GCP Project

First, set the project where you want to run the export. Replace `PROJECT_ID` with your project ID.
```bash
gcloud config set project PROJECT_ID
```

### Step 2: Execute the `gcloud` Asset Export

Before exporting assets, ensure you have created a dataset in BigQuery where the data will be stored. The export process is based on the `gcloud asset export` command, which allows you to export different asset types into a specified BigQuery table. You can export various asset types, such as resources, relationships, and OS inventory. Below are examples for exporting different content types to your BigQuery dataset.

#### Export Resources

To export resources, you can use the following command for either an organization or a folder. It is important to specify `--asset-types` to filter the types of resources you want to export. If you do not specify `--asset-types`, all resources will be exported. For example, if you only want to export instances, you should specify it as follows:

For Organization:
```bash
gcloud asset export \
  --organization=ORGANIZATION_ID \
  --billing-project=PROJECT_ID \
  --content-type=resource \
  --bigquery-table=projects/PROJECT_ID/datasets/DATASET_ID/tables/TABLE_ID \
  --asset-types="compute.googleapis.com/Instance" \
  --output-bigquery-force
```
For Folder:
```bash
gcloud asset export \
  --folder=FOLDER_ID \
  --billing-project=PROJECT_ID \
  --content-type=resource \
  --bigquery-table=projects/PROJECT_ID/datasets/DATASET_ID/tables/TABLE_ID \
  --asset-types="compute.googleapis.com/Instance" \
  --output-bigquery-force
```

#### Export Relationships

You can export relationships similarly:

```bash
gcloud asset export \
  --organization=ORGANIZATION_ID \
  --billing-project=PROJECT_ID \
  --content-type=relationship \
  --bigquery-table=projects/PROJECT_ID/datasets/DATASET_ID/tables/TABLE_ID \
  --output-bigquery-force
```

#### Export OS Inventory

Export OS inventory using:

```bash
gcloud asset export \
  --organization=ORGANIZATION_ID \
  --billing-project=PROJECT_ID \
  --content-type=os-inventory \
  --bigquery-table=projects/PROJECT_ID/datasets/DATASET_ID/tables/TABLE_ID \
  --output-bigquery-force
```

### Step 3: Partitioned Exports (Optional)

If you want to partition your exports by time, you can add the `--partition-key=request-time` flag.

```bash
gcloud asset export \
  --organization=ORGANIZATION_ID \
  --billing-project=PROJECT_ID \
  --content-type=resource \
  --bigquery-table=projects/PROJECT_ID/datasets/DATASET_ID/tables/TABLE_ID \
  --partition-key=request-time \
  --per-asset-type \
  --output-bigquery-force
```

***

## Automating the Export with Cloud Scheduler

To automate the export process, you can use **Cloud Scheduler** to send periodic requests to the **Asset Inventory API**. 

The Asset Inventory API allows you to manage and monitor all the resources in your Google Cloud Platform environment. Specifically, it enables you to export asset metadata, providing a comprehensive view of your GCP resources. By leveraging Cloud Scheduler with the Asset Inventory API, you can eliminate the need for manual command execution, allowing you to schedule regular exports at specified intervals. This integration ensures that your asset data is up-to-date.

<img src="https://github.com/user-attachments/assets/943b557a-dee8-4202-a98a-70c436f0720c" alt="asset1" width="800"/>

### Step 1: Create a Service Account

Create a service account to manage the Cloud Scheduler job and assign it the necessary roles.

#### Permissions for the Service Account

Assign the following roles to the service account:
- **Organization Level**:
  - `Cloud Asset Viewer`
  - `Organization Viewer`
- **Project Level**:
  - `BigQuery Data Editor`
  - `BigQuery User`

### Step 2: Enable the Asset Inventory API

Enable the Asset Inventory API in the project where the Cloud Scheduler job will run.

### Step 3: Set Up BigQuery

Create a BigQuery dataset to store the exported data.

### Step 4: Create a Cloud Scheduler Job

Set up a Cloud Scheduler job to make HTTP requests to the Asset Inventory API. Cloud Scheduler allows you to schedule virtually any job, such as executing HTTP requests or calling Cloud Pub/Sub. This is particularly useful for automating the export of asset data, ensuring that the data is updated at regular intervals without manual intervention.

To create a Cloud Scheduler job, you need to define the frequency of execution using a cron-style schedule. For example, you might use a schedule like `*/15 7-20 * * *` to run the job every 15 minutes between 7 AM and 8 PM. This flexibility allows you to customize how often the export occurs based on your needs.

#### Example Cloud Scheduler Job Configuration

- **Job Name**: asset-inventory-export
- **Target Type**: HTTP
- **URL**:
  - For organization-level export: `https://cloudasset.googleapis.com/v1/organizations/ORGANIZATION_ID:exportAssets`
  - For folder-level export: `https://cloudasset.googleapis.com/v1/folders/FOLDER_ID:exportAssets`

- **HTTP Headers**:
  - `Content-Type: application/json`
  - `User-Agent: Google-Cloud-Scheduler`

- **Request Body**:

  - Example for exporting organization-level instance resources.
```json
{
  "parent": "organizations/ORGANIZATION_ID",
  "contentType": "RESOURCE",
  "outputConfig": {
    "bigqueryDestination": {
      "dataset": "projects/PROJECT_ID/datasets/DATASET_ID",
      "table": "TABLE_NAME",
      "force": true,
      "separateTablesPerAssetType": true
    }
  },
  "assetTypes": [
    "compute.googleapis.com/Instance"
  ]
}
```

  - Example for exporting folder-level instance resources.
```json
{
  "parent": "folders/FOLDER_ID",
  "contentType": "RESOURCE",
  "outputConfig": {
    "bigqueryDestination": {
      "dataset": "projects/PROJECT_ID/datasets/DATASET_ID",
      "table": "TABLE_NAME",
      "force": true,
      "separateTablesPerAssetType": true
    }
  },
  "assetTypes": [
    "compute.googleapis.com/Instance"
  ]
}
```

- **Authorization**:

Add the OAuth token to authenticate the requests. Use the service account created earlier.

  - Auth Header: `Add OAuth token`
  - Scope: `https://www.googleapis.com/auth/cloud-platform`

***

## BigQuery Export Results and Asset Inventory Tables

After setting up the automated export, BigQuery provides a comprehensive view of all your GCP assets. The export process creates individual tables for each asset type in your GCP environment, making it easier to query and analyze your infrastructure.

### Dataset Structure and Asset Tables

The following image shows the BigQuery console view of the exported Asset Inventory tables in the dataset:

![bigquery_1_f](https://github.com/user-attachments/assets/f80a7d9c-b01c-410c-a19c-b2b2f0b5c294)

The export process creates tables following the naming pattern `[prefix]_[service]_googleapis_com_[resource]`. Each table contains detailed information about specific resource types across your GCP infrastructure. Here's the list of exported asset tables:

```sql
-- List of all Asset Inventory tables in BigQuery
all-asset-export_aiplatform_googleapis_com_Dataset
all-asset-export_aiplatform_googleapis_com_MetadataStore
all-asset-export_aiplatform_googleapis_com_NotebookRuntimeTemplate
all-asset-export_aiplatform_googleapis_com_TrainingPipeline
all-asset-export_apikeys_googleapis_com_Key
all-asset-export_artifactregistry_googleapis_com_DockerImage
all-asset-export_artifactregistry_googleapis_com_Repository
all-asset-export_backupdr_googleapis_com_ManagementServer
all-asset-export_bigquery_googleapis_com_Dataset
all-asset-export_bigquery_googleapis_com_Model
all-asset-export_bigquery_googleapis_com_Table
all-asset-export_bigquerydatatransfer_googleapis_com_TransferConfig
all-asset-export_certificatemanager_googleapis_com_Certificate
all-asset-export_certificatemanager_googleapis_com_CertificateMap
all-asset-export_certificatemanager_googleapis_com_CertificateMapEntry
all-asset-export_cloudbilling_googleapis_com_ProjectBillingInfo
all-asset-export_cloudbuild_googleapis_com_Build
all-asset-export_cloudbuild_googleapis_com_BuildTrigger
all-asset-export_cloudbuild_googleapis_com_Connection
all-asset-export_cloudbuild_googleapis_com_GlobalTriggerSettings
all-asset-export_cloudfunctions_googleapis_com_CloudFunction
all-asset-export_cloudfunctions_googleapis_com_Function
all-asset-export_cloudkms_googleapis_com_CryptoKey
all-asset-export_cloudkms_googleapis_com_CryptoKeyVersion
all-asset-export_cloudkms_googleapis_com_KeyRing
all-asset-export_cloudresourcemanager_googleapis_com_Folder
all-asset-export_cloudresourcemanager_googleapis_com_Project
all-asset-export_cloudresourcemanager_googleapis_com_TagBinding
all-asset-export_cloudresourcemanager_googleapis_com_TagKey
all-asset-export_cloudresourcemanager_googleapis_com_TagValue
all-asset-export_composer_googleapis_com_Environment
all-asset-export_compute_googleapis_com_Address
all-asset-export_compute_googleapis_com_Autoscaler
all-asset-export_compute_googleapis_com_BackendService
all-asset-export_compute_googleapis_com_Commitment
all-asset-export_compute_googleapis_com_Disk
all-asset-export_compute_googleapis_com_Firewall
all-asset-export_compute_googleapis_com_ForwardingRule
all-asset-export_compute_googleapis_com_GlobalAddress
all-asset-export_compute_googleapis_com_GlobalForwardingRule
all-asset-export_compute_googleapis_com_HealthCheck
all-asset-export_compute_googleapis_com_HttpHealthCheck
all-asset-export_compute_googleapis_com_Image
all-asset-export_compute_googleapis_com_Instance
all-asset-export_compute_googleapis_com_InstanceGroup
all-asset-export_compute_googleapis_com_InstanceGroupManager
all-asset-export_compute_googleapis_com_InstanceTemplate
all-asset-export_compute_googleapis_com_InterconnectAttachment
all-asset-export_compute_googleapis_com_MachineImage
all-asset-export_compute_googleapis_com_Network
all-asset-export_compute_googleapis_com_NetworkAttachment
all-asset-export_compute_googleapis_com_NetworkEndpointGroup
all-asset-export_compute_googleapis_com_Project
all-asset-export_compute_googleapis_com_RegionBackendService
all-asset-export_compute_googleapis_com_RegionDisk
all-asset-export_compute_googleapis_com_ResourcePolicy
all-asset-export_compute_googleapis_com_Route
all-asset-export_compute_googleapis_com_Router
all-asset-export_compute_googleapis_com_SecurityPolicy
all-asset-export_compute_googleapis_com_Snapshot
all-asset-export_compute_googleapis_com_SslCertificate
all-asset-export_compute_googleapis_com_SslPolicy
all-asset-export_compute_googleapis_com_Subnetwork
all-asset-export_compute_googleapis_com_TargetHttpProxy
all-asset-export_compute_googleapis_com_TargetHttpsProxy
all-asset-export_compute_googleapis_com_TargetInstance
all-asset-export_compute_googleapis_com_TargetPool
all-asset-export_compute_googleapis_com_TargetTcpProxy
all-asset-export_compute_googleapis_com_UrlMap
all-asset-export_container_googleapis_com_Cluster
all-asset-export_container_googleapis_com_NodePool
all-asset-export_containerregistry_googleapis_com_Image
all-asset-export_dataflow_googleapis_com_Job
all-asset-export_dataform_googleapis_com_Repository
all-asset-export_datafusion_googleapis_com_Instance
all-asset-export_datalineage_googleapis_com_Process
all-asset-export_dataplex_googleapis_com_EntryGroup
all-asset-export_dataproc_googleapis_com_AutoscalingPolicy
all-asset-export_dataproc_googleapis_com_Job
all-asset-export_datastream_googleapis_com_ConnectionProfile
all-asset-export_datastream_googleapis_com_PrivateConnection
all-asset-export_datastream_googleapis_com_Stream
all-asset-export_discoveryengine_googleapis_com_Collection
all-asset-export_discoveryengine_googleapis_com_DataStore
all-asset-export_discoveryengine_googleapis_com_Engine
all-asset-export_dns_googleapis_com_ManagedZone
all-asset-export_documentai_googleapis_com_HumanReviewConfig
all-asset-export_documentai_googleapis_com_Processor
all-asset-export_documentai_googleapis_com_ProcessorVersion
all-asset-export_gkebackup_googleapis_com_Backup
all-asset-export_gkebackup_googleapis_com_BackupPlan
all-asset-export_gkebackup_googleapis_com_Restore
all-asset-export_gkebackup_googleapis_com_RestorePlan
all-asset-export_gkebackup_googleapis_com_VolumeBackup
all-asset-export_iam_googleapis_com_Role
all-asset-export_iam_googleapis
```

***

## Slack Integration via GCP Cloud Function

This project includes a Cloud Function designed to integrate with Slack using Slash commands. It enables users to interactively query asset data stored in BigQuery directly from Slack. For instance, by issuing a command like `/getinfo <instance_id>`, users can retrieve detailed information about a specific virtual machine instance.

Key features of this integration:

- **Secure Request Verification**: Ensures that incoming requests are genuinely from Slack by validating the signature using Slack's signing secret.
- **Parameterized BigQuery Queries**: Executes secure, parameterized queries against BigQuery to fetch asset information.
- **Slack-Compatible Responses**: Formats responses using Slack's Block Kit for a user-friendly display within Slack.
- **Modular Design**: The Cloud Function is structured to allow easy extension for additional commands or functionalities.

This integration facilitates real-time access to asset inventory data, enhancing operational efficiency and collaboration within teams.

***

## Final Notes

- The exports are customizable. You can define specific asset types to focus on particular resources or export everything.
- Manual vs Automated: Use `gcloud` for one-time exports or Cloud Scheduler for regular automated exports.

TIME - 2026-01-15 12:10:58