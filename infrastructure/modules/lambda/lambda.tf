resource "aws_lambda_function" "test_lambda" {
  # If the file is not in the current working directory you will need to include a
  # path.module in the filename.
  filename      = "lambda_function_payload.zip"
  function_name = var.lambda_func_name
  role          = var.lambda_read_role_arn
  handler       = "lambda-function1.lambda_handler"

  source_code_hash = data.archive_file.lambda.output_base64sha256

  runtime = "python3.13"

  environment {
    variables = {
      foo = "bar"
    }
  }
}

data "archive_file" "lambda" {
  type        = "zip"
  source_file = "src/lambda-function1.py"
  output_path = "lambda_function_payload.zip"
}
