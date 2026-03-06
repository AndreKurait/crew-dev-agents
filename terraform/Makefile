.PHONY: auth init plan apply destroy kubeconfig

AWS_ACCOUNT ?= <ACCOUNT_ID>
AWS_REGION  ?= us-west-2

auth:
	ada credentials update --once --account $(AWS_ACCOUNT) --role <ROLE_NAME> --provider <PROVIDER>

init:
	terraform init

plan:
	terraform plan

apply:
	terraform apply

destroy:
	terraform destroy

kubeconfig:
	aws eks update-kubeconfig --region $(AWS_REGION) --name crew-dev-agents
