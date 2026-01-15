resource "aws_ecs_task_definition" "eligibility_api" {
  family                   = var.instance_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = var.eligibility_lambda_role_arn
  task_role_arn            = var.eligibility_lambda_role_arn

  container_definitions = jsonencode([
    {
      name  = "eligibility-api"
      image = "${var.ecr_repository_url}:latest"
      portMappings = [{ containerPort = 8000 }]
      environment = [
        { name = "PERSON_TABLE_NAME", value = var.eligibility_status_table_name },
        { name = "RULES_BUCKET_NAME", value = var.eligibility_rules_bucket_name },
        # ... other variables from your lambda environment block
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.instance_name}"
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_cluster" "main" {
  name = "${var.stack_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled" # Recommended for monitoring Fargate performance
  }

  tags = {
    Name        = "${var.stack_name}-cluster"
    Environment = var.environment
  }
}

resource "aws_ecs_service" "eligibility_service" {
  name            = "${var.instance_name}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.eligibility_api.arn
  launch_type     = "FARGATE"
  desired_count   = var.provisioned_concurrency_count

  network_configuration {
    subnets          = var.vpc_intra_subnets
    security_groups  = var.security_group_ids
    assign_public_ip = false
  }
}

