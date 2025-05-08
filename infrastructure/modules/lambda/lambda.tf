resource "aws_lambda_function" "eligibility_signposting_lambda" {
  # If the file is not in the current working directory you will need to include a
  # path.module in the filename.
  filename      = var.file_name
  function_name = var.lambda_func_name
  role          = var.eligibility_lambda_role_arn
  handler       = var.handler

  source_code_hash = data.archive_file.lambda.output_base64sha256

  runtime     = "python3.13"
  timeout     = 3   # Default
  memory_size = 128 # Default

  environment {
    variables = {
      foo = "bar"
    }
  }
  vpc_config {
    subnet_ids         = var.vpc_intra_subnets
    security_group_ids = var.security_group_ids
  }
}

data "archive_file" "lambda" {
  type        = "zip"
  source_file = var.lambda_app_source_file
  output_path = var.lambda_app_zip_output_path
}
