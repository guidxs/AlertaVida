# AlertaVida Terraform

This configuration manages one security group and one EC2 instance in the existing VPC and subnet. It does not create networking resources.

## Keep local state and variables outside the repository

The local backend requires an explicit external path when initializing. From this directory in PowerShell:

```powershell
$stateDir = Join-Path $env:LOCALAPPDATA 'AlertaVida'
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
Copy-Item .\terraform.tfvars.example (Join-Path $stateDir 'terraform.tfvars')
$backendConfig = "path=$(Join-Path $stateDir 'terraform.tfstate')"
terraform init "-backend-config=$backendConfig"
```

Edit the external `terraform.tfvars` if the SSH public IP changes. After AWS credentials are configured in the shell or AWS CLI profile, a plan can use:

```powershell
$tfvars = Join-Path $stateDir 'terraform.tfvars'
terraform plan "-var-file=$tfvars"
terraform apply "-var-file=$tfvars"
```

The initialized local backend keeps using the external state path for both `plan` and `apply`. Do not run `terraform init` without the external backend path. Real `.tfvars` files and Terraform state artifacts are ignored by the repository `.gitignore` as an additional safeguard.
