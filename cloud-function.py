# --- SCRIPT OVERVIEW ---
# This Google Cloud Function is designed to act as a backend for Slack slash commands.
# It listens for HTTP POST requests, expecting them to originate from Slack.
#
# Key functionalities:
# 1.  Request Handling (`request_handler`):
#     - Main entry point for HTTP requests.
#     - Verifies if the request comes from Slack by checking the Content-Type.
#     - Validates the Slack request signature using a shared secret (`verify_slack_signature`)
#       to ensure authenticity and integrity.
#     - Parses the command and parameters sent from Slack.
#     - Sanitizes the input parameter.
#     - Routes the command to the appropriate handler via `menu_controller`.
#
# 2.  Command Routing (`menu_controller`):
#     - Takes the parsed command and parameter.
#     - Directs the request to specific functions based on the command (e.g., `/getinfo`, `/checkstatus`).
#
# 3.  Data Retrieval and Formatting:
#     - `get_resource_info`:
#         - Queries a BigQuery table (specified by environment variables) to fetch details
#           about a given resource (e.g., a VM instance).
#         - Formats the retrieved data into Slack message blocks, including buttons for actions
#           (like opening the resource in the GCP console).
#     - `check_resource_status`:
#         - Queries a different BigQuery table to get status-related information for a resource.
#         - Formats a textual response for Slack indicating the resource's status.
#
# 4.  Slack Signature Verification (`verify_slack_signature`):
#     - Crucial security step. Uses the `slack_sdk` to verify that requests genuinely
#       originate from Slack, preventing spoofing. Relies on the `SLACK_SIGNING_SECRET`
#       environment variable.
#
# 5.  Configuration:
#     - Heavily relies on environment variables for:
#         - `SLACK_SIGNING_SECRET`: For request verification.
#         - `BIGQUERY_PROJECT_ID`: GCP Project ID for BigQuery.
#         - `BIGQUERY_DATASET_ID`: BigQuery Dataset ID.
#         - `INSTANCES_TABLE_ID`: BigQuery Table ID for general resource information.
#         - `STATUS_CHECK_TABLE_ID`: BigQuery Table ID for resource status checks.
#
# 6.  Logging:
#     - Uses Google Cloud Logging for structured logging throughout the execution flow,
#       aiding in debugging and monitoring.
#
# Expected Slack Commands (examples):
#   /getinfo <resource-name>
#   /checkstatus <resource-name>
#
# The function returns JSON payloads formatted for Slack's API, typically as
# ephemeral messages visible only to the user who invoked the command.
# --- END SCRIPT OVERVIEW ---

import functions_framework
from google.cloud import bigquery
from google.cloud import logging as cloud_logging
import logging
import os
import json
import re
from slack_sdk.signature import SignatureVerifier
from datetime import datetime # Added for generic timestamp formatting

# Set up Google Cloud logging client
logging_client = cloud_logging.Client()
logging_client.setup_logging()

# --- Configuration Constants (better as environment variables) ---
# TODO: Replace these default values or ensure environment variables are set.
# It's highly recommended to use environment variables for these in a real environment.
BIGQUERY_PROJECT_ID = os.environ.get("BIGQUERY_PROJECT_ID", "your-gcp-project-id")
BIGQUERY_DATASET_ID = os.environ.get("BIGQUERY_DATASET_ID", "your_dataset_id")
INSTANCES_TABLE_ID = os.environ.get("INSTANCES_TABLE_ID", "your_instances_table")
STATUS_CHECK_TABLE_ID = os.environ.get("STATUS_CHECK_TABLE_ID", "your_status_check_table")

# Essential: Environment variable for Slack signing secret
# You MUST configure this environment variable in your Cloud Function settings.
# SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
# The verify_slack_signature function already uses os.environ["SLACK_SIGNING_SECRET"]


@functions_framework.http
def request_handler(request):
    """
    Main entry point for the Cloud Function.
    Handles HTTP requests, verifies Slack signature, and routes commands.
    """
    try:
        if request.headers.get('Content-Type') == 'application/x-www-form-urlencoded': # Comes from Slack
            # Verify Slack signature before processing
            verify_slack_signature(request)
            logging.info(f"Slack request received. Headers: {dict(request.headers)}")
            logging.info(f"Request body (form): {json.dumps(dict(request.form), indent=2)}")

            input_data = request.form
            command = input_data.get('command', '').strip()
            parameter = input_data.get('text', '').strip()

            if not command:
                logging.warning("Command not provided in Slack request.")
                return {
                    "response_type": "ephemeral",
                    "text": "Error: No command was provided."
                }

            if not parameter or len(parameter.split()) > 1:
                logging.info(f"WARNING: A single parameter was expected for command '{command}'. Example: {command} my-resource")
                return {
                    "response_type": "ephemeral",
                    "text": f"Error: A single parameter was expected. Example: {command} my-resource"
                }

            # Sanitize parameter: allow only alphanumeric, underscores, and hyphens.
            parameter = re.sub(r'[^a-zA-Z0-9\-_]', '', parameter).lower()
            logging.info(f"Command '{command}' received with sanitized parameter: '{parameter}'")

            return menu_controller(command, parameter)
        else:
            logging.warning(f"Request received with unexpected Content-Type: {request.headers.get('Content-Type')}")
            logging.debug(f"Content of invalid request: {request.get_data(as_text=True)}")
            return ("This request does not appear to be from Slack (incorrect Content-Type).", 400)

    except ValueError as ve: # Specifically for signature or validation errors
        logging.error(f"Validation or signature error: {str(ve)}")
        return {
            "response_type": "ephemeral",
            "text": f"Validation Error: {str(ve)}"
        }
    except Exception as e:
        error_msg = str(e)
        logging.exception(f"GENERAL ERROR: Error processing request: {error_msg}") # Use logging.exception to include traceback
        return {
            "response_type": "ephemeral",
            "text": f"Sorry, an error occurred while processing your request. Please try again later."
        }

def menu_controller(command, parameter):
    """
    Routes the received command to the appropriate handler.
    """
    logging.info(f"Processing command '{command}' with parameter '{parameter}'")

    if command == '/getinfo': # Generic command to get information
        response_payload = get_resource_info(parameter)
        return response_payload

    elif command == '/checkstatus': # Generic command to check status
        response_payload = check_resource_status(parameter)
        return response_payload

    else:
        logging.warning(f"Unknown command: {command}")
        return {
            "response_type": "ephemeral",
            "text": f"Command '{command}' not recognized."
        }

def get_resource_info(resource_name):
    """
    Retrieves information for a resource (e.g., a VM) from BigQuery and formats it for Slack.
    """
    client = bigquery.Client()
    # TODO: Adapt this query to your instance/resource table schema.
    # Ensure that the fields you select (instance_id, instance_name, project_id, status, etc.)
    # exist in your table or adjust them accordingly.
    query = f"""
        SELECT
            instance_id,
            instance_name,
            project_id,  -- Ensure this field exists if you want to use it
            status,
            zone,
            machine_type,
            creation_timestamp, -- Or any date/time field you have
            -- Example of generic label fields you might have:
            -- labels.environment AS label_environment,
            -- labels.owner AS label_owner,
            CONCAT('https://console.cloud.google.com/compute/instancesDetail/zones/', zone, '/instances/', instance_name, '?project=', project_id) AS instance_console_url
        FROM `{BIGQUERY_PROJECT_ID}.{BIGQUERY_DATASET_ID}.{INSTANCES_TABLE_ID}`
        WHERE LOWER(instance_name) = @resource_name OR LOWER(instance_id) = @resource_name
        LIMIT 2 -- Limit in case of duplicates or to avoid overloading
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("resource_name", "STRING", resource_name)
        ]
    )

    logging.info(f"Executing BigQuery query to get resource information: {resource_name}")
    results = client.query(query, job_config=job_config).result()
    rows = list(results)

    if not rows:
        logging.warning(f"No information found for resource: {resource_name}")
        return {
            "response_type": "ephemeral",
            "text": f"No information found for resource: *{resource_name}*."
        }

    logging.info(f"Found {len(rows)} records for resource: {resource_name}")

    blocks = []
    for row in rows:
        # Format timestamp if it exists and is a datetime object
        formatted_time = "Not available"
        if row.creation_timestamp and hasattr(row.creation_timestamp, 'strftime'):
            formatted_time = row.creation_timestamp.strftime("%d-%m-%Y at %H:%M UTC")
        elif row.creation_timestamp:
            formatted_time = str(row.creation_timestamp)


        message_text = (
            f"ℹ️ Information for *{row.instance_name or 'N/A'}* (ID: *{row.instance_id or 'N/A'}*):\n"
            f"   • Project: *{row.project_id or 'N/A'}*\n"
            f"   • Status: *{row.status or 'N/A'}*\n"
            f"   • Zone: *{row.zone or 'N/A'}*\n"
            f"   • Machine Type: *{row.machine_type or 'N/A'}*\n"
            # Example with generic labels (uncomment and adapt if you have them):
            # f"   • Environment: *{getattr(row, 'label_environment', 'N/A')}*\n"
            # f"   • Owner: *{getattr(row, 'label_owner', 'N/A')}*\n"
            f"   • Created/Updated: _{formatted_time}_"
        )

        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": message_text}})

        action_elements = []
        if row.instance_console_url: # Make sure instance_console_url is selected in your query and exists
            action_elements.append(
                {"type": "button", "text": {"type": "plain_text", "text": "🔗 Open in GCP Console", "emoji": True}, "url": row.instance_console_url}
            )
        # You can add more buttons if you have other relevant URLs or actions
        # Example:
        # if row.project_id:
        #    action_elements.append(
        #        {"type": "button", "text": {"type": "plain_text", "text": "View Project", "emoji": True},
        #         "url": f"https://console.cloud.google.com/home/dashboard?project={row.project_id}"}
        #    )

        if action_elements:
            blocks.append({"type": "actions", "elements": action_elements})
        blocks.append({"type": "divider"})

    # Remove the last divider if it exists
    if blocks and blocks[-1]["type"] == "divider":
        blocks.pop()

    return {
        "response_type": "ephemeral", # "in_channel" for public response
        "blocks": blocks
    }


def check_resource_status(resource_name):
    """
    Checks the status of a resource (e.g., if it has a specific configuration) from BigQuery.
    """
    client = bigquery.Client()
    # TODO: Adapt this query to your "status" or "checks" table schema.
    # Ensure that the fields you select (item_name, current_status, details, last_checked)
    # exist in your table or adjust them accordingly.
    query = f"""
        SELECT
            item_name,      -- Name of the item/resource
            current_status, -- Current status of the check
            details,        -- Additional details
            last_checked    -- Timestamp of the last check
        FROM `{BIGQUERY_PROJECT_ID}.{BIGQUERY_DATASET_ID}.{STATUS_CHECK_TABLE_ID}`
        WHERE LOWER(item_name) = @resource_name
        LIMIT 1
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("resource_name", "STRING", resource_name)
        ]
    )

    logging.info(f"Executing BigQuery query to check resource status: {resource_name}")
    results = client.query(query, job_config=job_config).result()
    rows = list(results)

    if not rows:
        logging.info(f"Resource '{resource_name}' not found in the status check table.")
        return {
            "response_type": "ephemeral",
            "text": f"❓ Resource *{resource_name}* was not found for status check."
        }

    row = rows[0]
    logging.info(f"Record found for '{resource_name}': {dict(row)}")

    status_value = str(row.current_status).lower() if row.current_status is not None else "unknown"
    details_value = row.details or "No additional details."
    last_checked_time = "Not available"
    if row.last_checked and hasattr(row.last_checked, 'strftime'):
        last_checked_time = row.last_checked.strftime("%d-%m-%Y at %H:%M UTC")
    elif row.last_checked:
        last_checked_time = str(row.last_checked)


    # TODO: Adapt this status logic to your needs
    if "active" in status_value or "ok" in status_value or "complete" in status_value:
        emoji = "✅"
        message = f"Resource *{row.item_name or resource_name}* has a favorable status: *{row.current_status or 'N/A'}*."
    elif "pending" in status_value or "in progress" in status_value:
        emoji = "⏳"
        message = f"Resource *{row.item_name or resource_name}* has status: *{row.current_status or 'N/A'}*."
    else:
        emoji = "❌"
        message = f"Resource *{row.item_name or resource_name}* requires attention. Status: *{row.current_status or 'N/A'}*."

    full_response_text = (
        f"{emoji} {message}\n"
        f"   • Details: _{details_value}_\n"
        f"   • Last checked: _{last_checked_time}_"
    )

    return {
        "response_type": "ephemeral",
        "text": full_response_text
    }

def verify_slack_signature(request):
    """
    Verifies the Slack request signature to ensure it's authentic.
    Uses the "SLACK_SIGNING_SECRET" environment variable.
    """
    slack_signing_secret = os.environ.get("SLACK_SIGNING_SECRET")
    if not slack_signing_secret:
        logging.error("CRITICAL: The SLACK_SIGNING_SECRET environment variable is not set.")
        # In a production environment, you might want to fail more strictly here.
        # For development/testing, you could allow it to proceed with a warning,
        # but NEVER in production without verification.
        raise ValueError("Server configuration does not include Slack signing secret. Verification skipped (INSECURE).")


    verifier = SignatureVerifier(slack_signing_secret)
    request_body = request.get_data(as_text=True) # Slack sends data as application/x-www-form-urlencoded
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    signature = request.headers.get('X-Slack-Signature', '')

    logging.debug(f"Verifying signature: Timestamp='{timestamp}', Signature='{signature}'")
    # logging.debug(f"Request Body for signature: {request_body}") # Be careful with sensitive data in logs

    if not verifier.is_valid(body=request_body, timestamp=timestamp, signature=signature):
        logging.error("Error: Invalid Slack signature.")
        raise ValueError("Invalid Slack signature.")

    logging.info("Slack signature verified successfully.")
    return True

# Example of how you might want to test locally (this doesn't run in Cloud Functions directly)
if __name__ == '__main__':
    # This is only for facilitating local testing and is not part of the Cloud Functions deployment.
    # To test locally, you would need to simulate a Slack request.
    # The Google Cloud Functions Framework emulates the environment, so you can run it with:
    # functions-framework --target=request_handler --port=8080 --debug
    # And then send a POST request (e.g., with curl or Postman) to http://localhost:8080/

    print("This script is designed to be run as a Google Cloud Function.")
    print("For local testing with the Functions Framework:")
    print("1. Ensure you have 'functions-framework' installed (`pip install functions-framework`).")
    print("2. Set up necessary environment variables (e.g., SLACK_SIGNING_SECRET, BIGQUERY_PROJECT_ID, etc.).")
    print("3. Run: functions-framework --target=request_handler --port=8080")
    print("4. Send a POST request simulating a Slack call to http://localhost:8080/")

    # Example of how to set environment variables for a quick local test (not for production!):
    # os.environ["SLACK_SIGNING_SECRET"] = "your_real_secret_here_for_testing"
    # os.environ["BIGQUERY_PROJECT_ID"] = "your-gcp-project"
    # os.environ["BIGQUERY_DATASET_ID"] = "your_dataset"
    # os.environ["INSTANCES_TABLE_ID"] = "your_instances_table"
    # os.environ["STATUS_CHECK_TABLE_ID"] = "your_status_table"

    # Simple simulation (without real signature, verification would fail if active)
    # class MockRequest:
    #     def __init__(self, data, headers):
    #         self.form = data
    #         self.headers = headers
    #         self._body_data = "&".join([f"{k}={v}" for k,v in data.items()]).encode('utf-8')

    #     def get_data(self, as_text=False):
    #         return self._body_data.decode('utf-8') if as_text else self._body_data

    # mock_headers = {
    #     'Content-Type': 'application/x-www-form-urlencoded',
    #     # To pass verify_slack_signature, you'd need to generate a valid timestamp and signature.
    #     # 'X-Slack-Request-Timestamp': str(int(time.time())),
    #     # 'X-Slack-Signature': '...a_valid_signature_generated_with_the_secret...'
    # }
    # mock_form_data_info = {
    #     'command': '/getinfo',
    #     'text': 'my-test-instance'
    # }
    # mock_form_data_status = {
    #     'command': '/checkstatus',
    #     'text': 'another-instance'
    # }

    # if os.environ.get("SLACK_SIGNING_SECRET"):
    #     print("\nAttempting /getinfo call (will fail if signature is invalid or no secret):")
    #     # response = request_handler(MockRequest(mock_form_data_info, mock_headers))
    #     # print(json.dumps(response, indent=2))
    # else:
    #     print("\nSLACK_SIGNING_SECRET is not set. Signature verification will fail or be bypassed.")
