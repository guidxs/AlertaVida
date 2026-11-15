
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

O AWS Academy Learner Lab fornece credenciais temporárias. Quando uma sessão expirar, inicie o laboratório novamente e atualize as credenciais da AWS CLI com os novos valores disponibilizados em `AWS Details`. A expiração da sessão não exige repetir o provisionamento da infraestrutura.

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

**Importante:** se o endereço IP público do operador mudar, atualize a variável `ssh_cidr` no arquivo `terraform.tfvars`, mantendo o formato IPv4 `/32`. Em seguida, gere e revise um novo plano antes de aplicar qualquer alteração. Isso atualiza a regra de SSH do Security Group.

O endereço IP público da EC2 também pode mudar após a reinicialização de uma sessão do Learner Lab. Nesse caso, consulte os outputs ou o console AWS para obter o endereço atual. A mudança do IP público não significa, por si só, que seja necessário recriar a infraestrutura.

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

**AMI da instância:** a configuração utiliza um ID de AMI fixo para evitar substituições inesperadas da instância durante novos planejamentos. Atualizações de imagem devem ser feitas intencionalmente, após verificar a compatibilidade e revisar o plano do Terraform.

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
- Manter uma cópia de segurança do arquivo `terraform.tfstate` em local protegido.
- Evitar executar operações simultâneas de Terraform utilizando o mesmo estado local.

O `.gitignore` do repositório contém regras adicionais para evitar o versionamento acidental desses arquivos.

O arquivo `terraform.tfstate` é necessário para manter o vínculo entre a configuração e os recursos existentes na AWS. Preserve cópias de segurança protegidas e atualizadas. Se o estado for perdido ou ficar inconsistente, recupere-o antes de executar novas operações de provisionamento.
