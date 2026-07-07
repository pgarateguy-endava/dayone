# AWS access checklist (to request)

What to request so Lab 2/3 and the Bench production path unblock. Everything in this repo
runs locally **without** these; request them in parallel while developing.

## Minimum to run the real agents (Lab 2 / Bench with LLM)

- [ ] AWS account access via IAM Identity Center (SSO), dev/sandbox account.
- [ ] Region agreed with the team (default assumed: `us-east-1`).
- [ ] **Amazon Bedrock model access** enabled for Anthropic Claude models
      (e.g. `anthropic.claude-3-5-sonnet-20241022-v2:0` — check current model list).
- [ ] IAM permissions: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`.

## For the accelerator / AgentCore path (Lab 3)

- [ ] Permissions to deploy the CDK stacks of `sample-strands-agentcore-starter`:
      CloudFormation, IAM role creation, Cognito, DynamoDB, S3, Bedrock AgentCore
      (Runtime, Memory, Gateway), Bedrock Knowledge Bases, CloudWatch/X-Ray.
- [ ] Docker allowed locally (images for AgentCore Runtime) + Node.js for CDK.

## Bench production extras

- [ ] DynamoDB table (bench state) and S3 bucket (Endava profile docs for the KB).
- [ ] EventBridge Scheduler (twice-daily graph trigger).
- [ ] Teams: Incoming Webhook on the responsibles' channel (no AWS, request to IT/channel owner)
      or Graph API app registration if per-person DMs are needed.

## Nice to have

- [ ] Bedrock Guardrails creation rights (for B3 RAG).
- [ ] Read access to whatever LMS / course platform exposes progress (else keep self-declared).
