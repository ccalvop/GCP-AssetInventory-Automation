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

## Final Notes

- The exports are customizable. You can define specific asset types to focus on particular resources or export everything.
- Manual vs Automated: Use `gcloud` for one-time exports or Cloud Scheduler for regular automated exports.

TIME - 2024-11-13 15:34:06
TIME - 2024-12-15 11:37:41