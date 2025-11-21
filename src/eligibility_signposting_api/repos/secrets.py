from wireup import service

@service(qualifier="nhs_hmac_key")
def nhs_hmac_key_factory() -> bytes:
    return b"abc123" # salt

# import boto3
# from botocore.exceptions import ClientError
#
# secret_name = "eligibility-signposting-api-dev/hashing_secret"
# region_name = "eu-west-2"
#
# # Create a Secrets Manager client
# session = boto3.session.Session()
# client = session.client(
#     service_name='secretsmanager',
#     region_name=region_name
# )
#
# try:
#     get_secret_value_response = client.get_secret_value(
#         SecretId=secret_name
#     )
# except ClientError as e:
#     # For a list of exceptions thrown, see
#     # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
#     raise e
#
# secret = get_secret_value_response['SecretString']
