import argparse
import os

import requests
import tableauserverclient as TSC

SUPPORTED_EXTENSIONS = {".tds", ".tdsx", ".tde", ".hyper", ".parquet"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish a Tableau datasource to Tableau Server."
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
    new_data_file = "./converted.hyper"
    if not os.path.isfile(new_data_file):
        raise FileNotFoundError(f"Datasource file not found: {new_data_file}")

    validate_file_type(new_data_file)

    # Read from environment variables
    tableau_token_name = os.getenv("TABLEAU_TOKEN_NAME")
    tableau_token_value = os.getenv("TABLEAU_TOKEN_VALUE")
    tableau_site = os.getenv("TABLEAU_SITE_ID", "NHSD_DEV")
    tableau_server_url = os.getenv("TABLEAU_SERVER_URL")
    datasource_id = os.getenv("TABLEAU_DATE_SOURCE_ID")

    # Validate required env vars
    if not tableau_token_name or not tableau_token_value:
        raise EnvironmentError(
            "Missing Tableau credentials.\n"
            "Set TABLEAU_TOKEN_NAME and TABLEAU_TOKEN_VALUE environment variables."
        )

    tableau_auth = TSC.PersonalAccessTokenAuth(
        tableau_token_name,
        tableau_token_value,
        tableau_site,
    )

    server = TSC.Server(tableau_server_url, use_server_version=True)

    with server.auth.sign_in(tableau_auth):
        target_item = server.datasources.get_by_id(datasource_id)

        # Publish (overwrite)
        server.datasources.publish(
            target_item,
            new_data_file,
            mode=TSC.Server.PublishMode.Overwrite,
        )
        print("Data source file overwritten.")

        # Cache refresh ping
        workbook_name = "EligibilityData-DQMetrics"
        view_name = "DataQualityMetrics"

        base_url = tableau_server_url.rstrip('/')
        ping_url = f"{base_url}/views/{workbook_name}/{view_name}?:refresh=y"

        print(f"Pinging Tableau Server for cache refresh: {view_name}...")

        headers = {
            "X-Tableau-Auth": server.auth_token
        }

        try:
            response = requests.get(ping_url, headers=headers, timeout=30)

            if response.status_code == 200:
                print("Cache refresh triggered successfully.")
            else:
                print(f"Ping sent, response status: {response.status_code}")

        except Exception as e:
            print(f"Ping failed: {e}")

        print("-" * 30)
        print("FINISHED: Data overwritten + cache refresh triggered.")


if __name__ == "__main__":
    main()
