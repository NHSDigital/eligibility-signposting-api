resource "aws_lambda_function" "eligibility_signposting_lambda" {
  # If the file is not in the current working directory you will need to include a
  # path.module in the filename.
  filename      = "lambda_function_payload.zip"
  function_name = var.lambda_func_name
  role          = var.eligibility_lambda_role_arn
  handler       = "lambda_function1.lambda_handler"

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
  source_file = "src/lambda_function1.py"
  output_path = "src/lambda_function_payload.zip"
}
