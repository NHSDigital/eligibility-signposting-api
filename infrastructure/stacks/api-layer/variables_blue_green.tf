# Blue-Green Deployment Variables
variable "blue_traffic_weight" {
  description = "Percentage of traffic to route to blue environment (0-100)"
  type        = number
  default     = 100

  validation {
    condition     = var.blue_traffic_weight >= 0 && var.blue_traffic_weight <= 100
    error_message = "Blue traffic weight must be between 0 and 100."
  }
}

variable "blue_lambda_version" {
  description = "Lambda version for blue environment"
  type        = string
  default     = "$LATEST"
}

variable "green_lambda_version" {
  description = "Lambda version for green environment"
  type        = string
  default     = "$LATEST"
}

variable "enable_canary_deployment" {
  description = "Enable canary deployment with gradual traffic shifting"
  type        = bool
  default     = false
}
