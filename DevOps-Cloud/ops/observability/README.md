# Observabilidade do AlertaVida

## Arquitetura

O Prometheus coleta métricas do backend FastAPI e do Node Exporter a cada 30 segundos. Os dois contêineres de monitoramento utilizam a rede `observability` do Docker Compose, configurada como `internal` (rede isolada). O backend também participa dessa rede e da rede padrão do Compose. A rede padrão permanece não isolada para permitir que o backend acesse o Databricks e que o frontend se comunique com o backend.

O Node Exporter é executado com o usuário sem privilégios `nobody`. Ele recebe montagens somente para leitura de `/proc`, `/sys` e do sistema de arquivos raiz do host. Apenas os coletores necessários para CPU, disco, sistema de arquivos, carga, memória e informações do sistema estão habilitados. O serviço não utiliza a rede ou o PID do host e não recebe capacidades adicionais do Linux.

## Serviços, portas e recursos

Os dois serviços de monitoramento são opcionais e só são iniciados com o perfil `observability` do Docker Compose:

- `prometheus:v3.15.1`: porta interna 9090, publicada no host somente em `127.0.0.1:9090`. Limite de memória de 384 MiB e CPU de 0,25.
- `node-exporter:v1.12.1`: porta interna 9100, acessível somente pela rede interna. Limite de memória de 64 MiB e CPU de 0,10.

Ambos utilizam `restart: unless-stopped`, sistema de arquivos do contêiner somente para leitura, remoção de capacidades adicionais, `no-new-privileges` e limites para os logs JSON do Docker (10 MiB por arquivo, com três arquivos).

A aplicação continua publicando somente a porta já utilizada pelo frontend. A porta 8000 do backend não é publicada diretamente no host.

## Armazenamento e retenção do Prometheus

Os dados do Prometheus são armazenados no volume Docker nomeado `alertavida_prometheus_data`. Esse volume permanece disponível mesmo após a substituição do contêiner ou um rollback da aplicação.

A retenção está configurada para sete dias, com limite lógico de 512 MB para o armazenamento TSDB. Essa configuração não representa uma cota rígida para todo o sistema de arquivos: arquivos WAL e outros dados do Docker também consomem espaço em disco.

O volume raiz da instância EC2 está configurado com 8 GB. Camadas de imagens Docker, cache de build, logs da aplicação e volume do Prometheus compartilham esse espaço. Por isso, a verificação de espaço livre do script de deploy deve ser mantida. Durante a manutenção, consulte `df -h` e `docker system df`. Não remova imagens de rollback ou volumes sem antes avaliar a necessidade de retenção.

## Acesso ao Prometheus por túnel SSH

O Prometheus fica vinculado ao endereço de loopback da EC2, sem exposição nas interfaces públicas. Na máquina do operador, abra um túnel utilizando o endereço IP público ou DNS da instância:

```bash
ssh -L 9090:127.0.0.1:9090 ec2-user@<EC2_PUBLIC_IP_OR_DNS>
```

No AWS Academy Learner Lab, o IP público da instância pode mudar após a reinicialização de uma sessão. Nesse caso, consulte o novo endereço da EC2 e atualize o comando SSH antes de restabelecer o túnel. O terminal que mantém o túnel deve permanecer aberto enquanto o Grafana estiver sendo utilizado.

Mantenha o terminal aberto e acesse:

`http://localhost:9090`

O Security Group da EC2 deve continuar restringindo o acesso SSH ao endereço `/32` autorizado do operador. Não adicione regras de entrada para as portas 9090 ou 9100.

## Acesso ao Grafana local

O Grafana é executado localmente na máquina do operador, por meio do arquivo `compose.grafana.local.yaml`. Ele não é publicado diretamente na internet e fica vinculado somente a `127.0.0.1:3000`.

Para acessar os dados do Prometheus implantado na EC2, primeiro estabeleça o túnel SSH descrito na seção anterior. Em seguida, inicie o Grafana local, a partir da raiz do repositório:

```bash
docker compose -f compose.grafana.local.yaml up -d
```

Acesse `http://localhost:3000` no navegador. A configuração de provisionamento carrega automaticamente a fonte de dados Prometheus e o dashboard do AlertaVida.

O dashboard apresenta os seguintes indicadores:

- Disponibilidade do backend.
- Taxa de requisições.
- Percentual de respostas HTTP 5xx.
- Latência p95 das requisições.
- Uso de CPU da instância EC2.

O Grafana utiliza o endereço `http://host.docker.internal:9090` para acessar o Prometheus pelo túnel SSH. O acesso inicial utiliza as credenciais padrão da imagem; altere a senha no primeiro acesso.

## Regras de alerta

As regras de alerta são definidas em `DevOps-Cloud/ops/observability/alerts.yml` e carregadas pelo Prometheus.

O projeto possui três regras permanentes:

| Regra | Condição de disparo | Duração | Severidade |
|---|---|---|---|
| `AlertaVidaBackendDown` | O backend deixa de responder às coletas do Prometheus (`up == 0`). | 1 minuto | Critical |
| `AlertaVidaHighErrorRate` | A taxa de respostas HTTP 5xx ultrapassa 5%, considerando uma janela de 5 minutos e desde que existam requisições. | 2 minutos | Warning |
| `AlertaVidaHighLatency` | A latência p95 das requisições ultrapassa 1 segundo, considerando uma janela de 5 minutos. | 2 minutos | Warning |

As regras são avaliadas pelo Prometheus e podem ser consultadas em sua interface, na seção **Alerts**.

Uma regra temporária também foi utilizada durante a validação do mecanismo de alertas no Grafana. Ela foi removida após o teste e não faz parte da configuração permanente do projeto.

## Verificação e consulta de logs

Execute os comandos abaixo no terminal da EC2, a partir do diretório do repositório. Eles não exibem os valores das variáveis de ambiente do Compose:

```bash
WEB_PORT=80 docker compose -p alertavida --profile observability ps
WEB_PORT=80 docker compose -p alertavida --profile observability logs --tail=100 prometheus node-exporter
WEB_PORT=80 docker compose -p alertavida --profile observability exec prometheus \
  /bin/busybox wget -q -O - http://127.0.0.1:9090/-/healthy
```

Na interface do Prometheus, acesse **Status → Targets**. Os alvos `alertavida-backend` e `ec2-node` devem aparecer com o estado `UP`.

## Recuperação do monitoramento sem alterar o MVP

O script de deploy trata a atualização e a verificação de saúde dos serviços `backend` e `frontend` como a transação principal. Depois, inicia ou atualiza os serviços de monitoramento em uma etapa independente, de melhor esforço.

Uma falha no monitoramento é registrada como aviso e não altera o SHA implantado do MVP nem provoca rollback da aplicação. Quando o SHA aprovado já está implantado, as próximas execuções do timer tentam novamente reconciliar os serviços de monitoramento.

Para tentar recuperar o monitoramento manualmente, sem reiniciar os contêineres da aplicação:

```bash
WEB_PORT=80 docker compose -p alertavida --profile observability \
  up -d --no-build prometheus node-exporter
```

Consulte os logs utilizando o comando apresentado na seção anterior. Durante a recuperação, não execute `docker compose down` nem remova o volume `alertavida_prometheus_data`, pois isso pode interromper a aplicação ou apagar os dados históricos do monitoramento.
