
# AlertaVida - Infraestrutura com Terraform

Este diretório contém a configuração do Terraform responsável por provisionar a infraestrutura do AlertaVida na AWS.

A configuração cria:
- Uma instância EC2 para hospedar a aplicação.
- Um Security Group com as regras de acesso necessárias.

São utilizados a VPC e a subnet existentes na conta AWS. O Terraform não cria novos recursos de rede.

## 1. Pré-requisitos

Antes de executar o Terraform, é necessário ter instalado:

- [Terraform](https://developer.hashicorp.com/terraform/install)
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

Também é necessário configurar as credenciais temporárias da AWS Academy Learner Lab no ambiente local.

Para verificar se as credenciais estão funcionando:

```powershell
aws sts get-caller-identity
```

## 2. Preparar os arquivos locais

Por segurança, o arquivo de estado do Terraform (`terraform.tfstate`), as variáveis reais (`terraform.tfvars`) e o plano de execução serão armazenados fora do repositório.

No PowerShell, a partir deste diretório:

```powershell
$stateDir = Join-Path $env:LOCALAPPDATA 'AlertaVida'
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

$tfvars = Join-Path $stateDir 'terraform.tfvars'
$tfstate = Join-Path $stateDir 'terraform.tfstate'
$tfplan = Join-Path $stateDir 'alertavida.tfplan'

if (-not (Test-Path $tfvars)) {
    Copy-Item .\terraform.tfvars.example $tfvars
}
```

Edite o arquivo `terraform.tfvars` criado no diretório local e preencha os valores correspondentes ao ambiente AWS:

```powershell
notepad $tfvars
```

O arquivo de exemplo contém as variáveis necessárias para configurar a região, a VPC, a subnet, o par de chaves e o endereço IP autorizado a acessar a instância por SSH.

**Importante:** se o endereço IP público utilizado para SSH mudar, atualize a variável `ssh_cidr` antes de executar o planejamento.

## 3. Inicializar o Terraform

Inicialize o Terraform informando explicitamente o caminho externo do arquivo de estado:

```powershell
terraform init "-backend-config=path=$tfstate"
```

Esse procedimento garante que o estado seja mantido fora do repositório.

Não execute `terraform init` sem informar o caminho externo do estado.

## 4. Planejar a infraestrutura

Gere um plano de execução:

```powershell
terraform plan "-var-file=$tfvars" "-out=$tfplan"
```

Antes de aplicar as alterações, revise o plano salvo:

```powershell
terraform show $tfplan
```

Confira os recursos que serão criados, modificados ou removidos. Não prossiga caso o plano apresente alterações inesperadas.

## 5. Aplicar a infraestrutura

Depois de revisar e confirmar o plano, aplique-o:

```powershell
terraform apply $tfplan
```

Ao finalizar, o Terraform apresentará os outputs da infraestrutura, incluindo o ID da instância EC2, o endereço IP público e o DNS público.

## 6. Segurança e boas práticas

- Não versionar arquivos `terraform.tfstate`, `terraform.tfvars` ou planos de execução.
- Não armazenar credenciais da AWS ou chaves privadas no repositório.
- Utilizar credenciais temporárias fornecidas pela AWS Academy Learner Lab.
- Restringir o acesso SSH ao endereço IP público autorizado, utilizando `/32`.
- Não expor a porta administrativa SSH para `0.0.0.0/0`.
- Manter o estado e as variáveis reais fora do diretório do projeto.

O `.gitignore` do repositório contém regras adicionais para evitar o versionamento acidental desses arquivos.
