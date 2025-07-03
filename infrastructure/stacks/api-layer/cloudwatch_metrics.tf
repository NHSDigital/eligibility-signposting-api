locals {
  cloudtrail_custom_metrics = [
    {
      name           = "UnauthorizedApiCalls"
      namespace      = "security"
      filter         = "{($.errorCode=\"*UnauthorizedOperation\") || ($.errorCode=\"AccessDenied*\")}"
      log_group_name = "NHSDAudit_trail_log_group"
    },
    {
      name           = "ConsoleAuthenticationFailures"
      namespace      = "security"
      filter         = "{($.eventName=ConsoleLogin) && ($.errorMessage=\"Failed authentication\")}"
      log_group_name = "NHSDAudit_trail_log_group"
    },
    {
      name           = "CloudTrailConfigChanges"
      namespace      = "security"
      filter         = "{($.eventName=CreateTrail) || ($.eventName=UpdateTrail) || ($.eventName=DeleteTrail) || ($.eventName=StartLogging) || ($.eventName=StopLogging)}"
      log_group_name = "NHSDAudit_trail_log_group"
    },
    {
      name           = "VPCChanges"
      namespace      = "security"
      filter         = "{($.eventName=CreateVpc) || ($.eventName=DeleteVpc) || ($.eventName=ModifyVpcAttribute) || ($.eventName=AcceptVpcPeeringConnection) || ($.eventName=CreateVpcPeeringConnection) || ($.eventName=DeleteVpcPeeringConnection) || ($.eventName=RejectVpcPeeringConnection) || ($.eventName=AttachClassicLinkVpc) || ($.eventName=DetachClassicLinkVpc) || ($.eventName=DisableVpcClassicLink) || ($.eventName=EnableVpcClassicLink)}"
      log_group_name = "NHSDAudit_trail_log_group"
    },
    {
      name           = "AWSConfigChanges"
      namespace      = "security"
      filter         = "{($.eventSource=config.amazonaws.com) && (($.eventName=StopConfigurationRecorder) || ($.eventName=DeleteDeliveryChannel) || ($.eventName=PutDeliveryChannel) || ($.eventName=PutConfigurationRecorder))}"
      log_group_name = "NHSDAudit_trail_log_group"
    },
    {
      name           = "ModificationOfCMKs"
      namespace      = "security"
      filter         = "{($.eventSource=kms.amazonaws.com) && (($.eventName=DisableKey) || ($.eventName=ScheduleKeyDeletion))}"
      log_group_name = "NHSDAudit_trail_log_group"
    },
    {
      name           = "UnsuccessfulSwitchRole"
      namespace      = "security"
      filter         = "{ ( $.eventName = SwitchRole  &&  $.responseElements.SwitchRole = Failure ) }"
      log_group_name = "NHSDAudit_trail_log_group"
    },
    {
      name           = "ConsoleLoginNoMFA"
      namespace      = "security"
      filter         = "{ ($.eventName = \"ConsoleLogin\") && ($.additionalEventData.MFAUsed != \"Yes\") && ($.userIdentity.type = \"IAMUser\") && ($.responseElements.ConsoleLogin = \"Success\") }"
      log_group_name = "NHSDAudit_trail_log_group"
    },
    {
      name           = "RootAccountUsage"
      namespace      = "security"
      filter         = "{$.userIdentity.type=\"Root\" && $.userIdentity.invokedBy NOT EXISTS && $.eventType !=\"AwsServiceEvent\"}"
      log_group_name = "NHSDAudit_trail_log_group"
    },
    {
      name           = "SecurityGroupChange"
      namespace      = "security"
      filter         = "{($.eventName=AuthorizeSecurityGroupIngress) || ($.eventName=AuthorizeSecurityGroupEgress) || ($.eventName=RevokeSecurityGroupIngress) || ($.eventName=RevokeSecurityGroupEgress) || ($.eventName=CreateSecurityGroup) || ($.eventName=DeleteSecurityGroup)}"
      log_group_name = "NHSDAudit_trail_log_group"
    },
    {
      name           = "RouteTableChanges"
      namespace      = "security"
      filter         = "{($.eventSource=ec2.amazonaws.com) && (($.eventName=CreateRoute) || ($.eventName=CreateRouteTable) || ($.eventName=ReplaceRoute) || ($.eventName=ReplaceRouteTableAssociation) || ($.eventName=DeleteRouteTable) || ($.eventName=DeleteRoute) || ($.eventName=DisassociateRouteTable))}"
      log_group_name = "NHSDAudit_trail_log_group"
    },
    {
      name           = "IAMPolicyChanges"
      namespace      = "security"
      filter         = "{($.eventSource=iam.amazonaws.com) && (($.eventName=DeleteGroupPolicy) || ($.eventName=DeleteRolePolicy) || ($.eventName=DeleteUserPolicy) || ($.eventName=PutGroupPolicy) || ($.eventName=PutRolePolicy) || ($.eventName=PutUserPolicy) || ($.eventName=CreatePolicy) || ($.eventName=DeletePolicy) || ($.eventName=CreatePolicyVersion) || ($.eventName=DeletePolicyVersion) || ($.eventName=AttachRolePolicy) || ($.eventName=DetachRolePolicy) || ($.eventName=AttachUserPolicy) || ($.eventName=DetachUserPolicy) || ($.eventName=AttachGroupPolicy) || ($.eventName=DetachGroupPolicy))}"
      log_group_name = "NHSDAudit_trail_log_group"
    },
    {
      name           = "s3BucketPolicyChanges"
      namespace      = "security"
      filter         = "{($.eventSource=s3.amazonaws.com) && (($.eventName=PutBucketAcl) || ($.eventName=PutBucketPolicy) || ($.eventName=PutBucketCors) || ($.eventName=PutBucketLifecycle) || ($.eventName=PutBucketReplication) || ($.eventName=DeleteBucketPolicy) || ($.eventName=DeleteBucketCors) || ($.eventName=DeleteBucketLifecycle) || ($.eventName=DeleteBucketReplication))}"
      log_group_name = "NHSDAudit_trail_log_group"
    },
    {
      name           = "ChangesToNetworkGateways"
      namespace      = "security"
      filter         = "{($.eventName=CreateCustomerGateway) || ($.eventName=DeleteCustomerGateway) || ($.eventName=AttachInternetGateway) || ($.eventName=CreateInternetGateway) || ($.eventName=DeleteInternetGateway) || ($.eventName=DetachInternetGateway)}"
      log_group_name = "NHSDAudit_trail_log_group"
    },
    {
      name           = "ChangesToNACLs"
      namespace      = "security"
      filter         = "{($.eventName=CreateNetworkAcl) || ($.eventName=CreateNetworkAclEntry) || ($.eventName=DeleteNetworkAcl) || ($.eventName=DeleteNetworkAclEntry) || ($.eventName=ReplaceNetworkAclEntry) || ($.eventName=ReplaceNetworkAclAssociation)}"
      log_group_name = "NHSDAudit_trail_log_group"
    },
    {
      name           = "KMSKeyPolicyChanges"
      namespace      = "security"
      filter         = "{($.eventSource=kms.amazonaws.com) && (($.eventName=PutKeyPolicy) || ($.eventName=DeleteKeyPolicy))}"
      log_group_name = "NHSDAudit_trail_log_group"
    },
    {
      name           = "s3PublicAccessChanges"
      namespace      = "security"
      filter         = "{($.eventSource=s3.amazonaws.com) && (($.eventName=PutBucketAcl) || ($.eventName=PutObjectAcl))}"
      log_group_name = "NHSDAudit_trail_log_group"
    },
    {
      name           = "CloudWatchAlarmChanges"
      namespace      = "security"
      filter         = "{($.eventSource=cloudwatch.amazonaws.com) && (($.eventName=PutMetricAlarm) || ($.eventName=DeleteAlarms) || ($.eventName=SetAlarmState))}"
      log_group_name = "NHSDAudit_trail_log_group"
    },
    {
      name           = "LambdaFunctionChanges"
      namespace      = "security"
      filter         = "{($.eventSource=lambda.amazonaws.com) && (($.eventName=CreateFunction20150331) || ($.eventName=DeleteFunction20150331) || ($.eventName=UpdateFunctionCode20150331) || ($.eventName=UpdateFunctionConfiguration20150331))}"
      log_group_name = "NHSDAudit_trail_log_group"
    },
  ]
}

resource "aws_cloudwatch_log_metric_filter" "cloudtrail_custom_metrics" {
  for_each = { for metric in local.cloudtrail_custom_metrics : metric.name => metric }

  name           = each.value.name
  log_group_name = each.value.log_group_name
  pattern        = each.value.filter

  metric_transformation {
    name      = each.value.name
    namespace = each.value.namespace
    value     = "1"
  }
}
