import argparse
import os
import sys

import requests
import tableauserverclient as TSC

SUPPORTED_EXTENSIONS = {".tds", ".tdsx", ".tde", ".hyper", ".parquet"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish a Tableau datasource to Tableau Server."
    )
    # Added a flag to control whether cache refresh failure should crash the script
    parser.add_argument(
        "--ignore-refresh-failure",
        action="store_true",
        help="Do not exit with error if the cache refresh ping fails."
    )
    return parser.parse_args()


def validate_file_type(file_path: str) -> None:
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported datasource file type '{file_extension}'. "
            f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )


def main() -> None:
    args = parse_args()
    new_data_file = "./converted.hyper"

    if not os.path.isfile(new_data_file):
        raise FileNotFoundError(f"Datasource file not found: {new_data_file}")

    validate_file_type(new_data_file)

    # --- Environment Variable Validation ---
    tableau_token_name = os.getenv("TABLEAU_TOKEN_NAME")
    tableau_token_value = os.getenv("TABLEAU_TOKEN_VALUE")
    tableau_server_url = os.getenv("TABLEAU_SERVER_URL")
    datasource_id = os.getenv("TABLEAU_DATASOURCE_ID")
    tableau_site = os.getenv("TABLEAU_SITE_ID", "NHSD_DEV")

    missing_vars = []
    if not tableau_token_name: missing_vars.append("TABLEAU_TOKEN_NAME")
    if not tableau_token_value: missing_vars.append("TABLEAU_TOKEN_VALUE")
    if not tableau_server_url: missing_vars.append("TABLEAU_SERVER_URL")
    if not datasource_id: missing_vars.append("TABLEAU_DATASOURCE_ID/TABLEAU_DATE_SOURCE_ID")

    if missing_vars:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing_vars)}. "
            "Please ensure your environment is configured correctly."
        )

    # --- Tableau Operations ---
    tableau_auth = TSC.PersonalAccessTokenAuth(
        tableau_token_name,
        tableau_token_value,
        tableau_site,
    )

    server = TSC.Server(tableau_server_url, use_server_version=True)

    with server.auth.sign_in(tableau_auth):
        print(f"Signing into {tableau_server_url} (Site: {tableau_site})...")
        target_item = server.datasources.get_by_id(datasource_id)

        # Publish (overwrite)
        server.datasources.publish(
            target_item,
            new_data_file,
            mode=TSC.Server.PublishMode.Overwrite,
        )
        print(f"Successfully overwritten datasource ID: {datasource_id}")

        # --- Cache Refresh Ping ---
        workbook_name = "EligibilityData-DQMetrics"
        view_name = "DataQualityMetrics"
        base_url = tableau_server_url.rstrip('/')
        ping_url = f"{base_url}/views/{workbook_name}/{view_name}?:refresh=y"

        print(f"Pinging Tableau Server for cache refresh: {view_name}...")

        headers = {"X-Tableau-Auth": server.auth_token}

        try:
            response = requests.get(ping_url, headers=headers, timeout=30)
            response.raise_for_status()  # Raises HTTPError for 4xx/5xx responses
            print("Cache refresh triggered successfully.")

        except Exception as e:
            error_msg = f"CRITICAL: Cache refresh failed: {e}"
            if args.ignore_refresh_failure:
                print(f"WARNING: {error_msg} (Continuing due to --ignore-refresh-failure)")
            else:
                print(error_msg)
                sys.exit(1)  # Exit with error code for CI visibility

        print("-" * 30)
        print("FINISHED: Data overwritten and refresh processed.")


if __name__ == "__main__":
    main()
