# Deploy na AWS

Runbook manual (sem Terraform) do único ambiente do Hevo hoje:
**app.hevo.ia.br**. Depois do setup inicial abaixo (já feito), todo push
em `main` builda a imagem e reimplanta sozinho — não tem outro branch nem
outro ambiente disparando deploy.

Arquitetura: 1 instância EC2 rodando Docker Compose (web + celery worker +
celery beat + redis + Postgres em container + Caddy pra HTTPS). Um único
domínio: `app.hevo.ia.br`.

> Existiu um ambiente `dev.hevo.ia.br` separado até setembro/2026 — foi
> aposentado e a mesma instância EC2 virou o `app.hevo.ia.br` atual (troca
> de domínio/config via SSH, sem provisionar máquina nova). Se você vir
> referências a `hevo-dev`/`hevo-dev-sg`/`hevo:dev` em tags ou nomes de
> recurso na AWS, é sobra cosmética dessa migração — não há mais nada
> rodando neles.

Substitua `<ACCOUNT_ID>` pelo seu AWS Account ID em todos os comandos
abaixo. Região: `us-east-2`.

## 1. ECR — repositório de imagens

```bash
aws ecr create-repository --repository-name hevo --region us-east-2
```

## 2. IAM role pro GitHub Actions (OIDC, sem chave fixa)

Criar o provider OIDC do GitHub (uma vez por conta AWS). O thumbprint não é
verificado de fato pela AWS pra esse provider, mas o parâmetro exige 40 hex
chars — pegue o valor real do certificado em vez de copiar um fixo:

```bash
THUMBPRINT=$(echo | openssl s_client -servername token.actions.githubusercontent.com \
  -connect token.actions.githubusercontent.com:443 2>/dev/null | \
  openssl x509 -fingerprint -sha1 -noout | sed 's/.*=//; s/://g' | tr 'A-Z' 'a-z')

aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list "$THUMBPRINT"
```

Trust policy (`trust.json`) — restringe a role ao repo `rsard/hevo`. O
GitHub inclui IDs numéricos imutáveis no claim `sub`
(`repo:rsard@<id>/hevo@<id>:ref:...`, não só `repo:rsard/hevo:ref:...`) —
o wildcard cobre isso:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:rsard@*/hevo@*:ref:refs/heads/*"
      }
    }
  }]
}
```

Policy de permissão (`ecr-push.json`) — só o necessário pra buildar/publicar:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "arn:aws:ecr:us-east-2:<ACCOUNT_ID>:repository/hevo"
    }
  ]
}
```

```bash
aws iam create-role --role-name github-actions-hevo \
  --assume-role-policy-document file://trust.json

aws iam put-role-policy --role-name github-actions-hevo \
  --policy-name ecr-push --policy-document file://ecr-push.json
```

Guarde o ARN da role (`arn:aws:iam::<ACCOUNT_ID>:role/github-actions-hevo`) —
vai virar o secret `AWS_ROLE_ARN` no GitHub (passo 9).

## 3. IAM role pra EC2 puxar do ECR

A instância usa uma instance profile em vez de chaves fixas:

```bash
aws iam create-role --role-name hevo-ec2-ecr-pull \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam attach-role-policy --role-name hevo-ec2-ecr-pull \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

aws iam create-instance-profile --instance-profile-name hevo-ec2-ecr-pull
aws iam add-role-to-instance-profile \
  --instance-profile-name hevo-ec2-ecr-pull --role-name hevo-ec2-ecr-pull
```

## 4. S3

Bucket `hevo-prod`, usado pra media (propostas em PDF, etc). Confirme que o
IAM user cujas chaves vão pro `.env` (as credenciais S3-only do app, não a
sua conta pessoal) tem acesso a ele.

## 5. Security group

```bash
aws ec2 create-security-group --group-name hevo-prod-sg \
  --description "Hevo app.hevo.ia.br" --vpc-id <VPC_ID>

# 80/443 abertos, 22 aberto pra internet
aws ec2 authorize-security-group-ingress --group-id <SG_ID> \
  --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id <SG_ID> \
  --protocol tcp --port 443 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id <SG_ID> \
  --protocol tcp --port 22 --cidr 0.0.0.0/0
```

22 fica aberto pro mundo porque o deploy do GitHub Actions conecta via SSH
a partir de IPs dinâmicos dos runners — não dá pra restringir por CIDR fixo.
Autenticação continua só por chave (sem senha, padrão do AL2023), então o
risco prático é baixo, mas é bom saber que está exposto.

## 6. Instância EC2

Amazon Linux 2023 (arm64), Docker + Compose instalados via user-data.
`t4g.micro` (2 vCPU, 1GB RAM) — `t4g.nano` seria mais barato mas essa conta
está restrita a tipos elegíveis pro Free Tier (`describe-instance-types
--filters Name=free-tier-eligible,Values=true` mostra quais); `t4g.micro`
está na lista, `t4g.nano` não. Com Django + Redis + 2 processos Celery,
1GB é justo — o user-data já sobe um swapfile pra evitar OOM kill em picos.
Se começar a faltar memória mesmo com swap, o próximo degrau é `t4g.small`
(2GB, ~$12/mês — `stop` → `modify-instance-attribute` → `start`, sem
recriar nada).

`user-data.sh`:

```bash
#!/bin/bash
dnf install -y docker
systemctl enable --now docker
usermod -aG docker ec2-user
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-aarch64 \
  -o /usr/libexec/docker/cli-plugins/docker-compose
chmod +x /usr/libexec/docker/cli-plugins/docker-compose
mkdir -p /opt/hevo && chown ec2-user:ec2-user /opt/hevo

# swap — t4g.micro só tem 1GB de RAM
fallocate -l 1G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

```bash
aws ec2 run-instances --image-id <AL2023_ARM64_AMI_ID> \
  --instance-type t4g.micro --key-name <SEU_KEY_PAIR> \
  --security-group-ids <SG_ID> \
  --iam-instance-profile Name=hevo-ec2-ecr-pull \
  --user-data file://user-data.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=hevo-prod}]'
```

Aloque um Elastic IP (`aws ec2 allocate-address` + `associate-address`) pra
o IP não mudar em um restart.

## 7. DNS

`hevo.ia.br` provavelmente está no Registro.br (não Route53) — não é preciso
criar hosted zone paga. Crie:

- `A app.hevo.ia.br` → Elastic IP da instância

## 8. Configurar o servidor

Via SSH:

```bash
ssh ec2-user@<IP>
sudo mkdir -p /opt/hevo && sudo chown ec2-user:ec2-user /opt/hevo
```

Copie do repo pra `/opt/hevo/` (via `scp` local):

- `deploy/docker-compose.yml` → `/opt/hevo/docker-compose.yml`
- `deploy/Caddyfile` → `/opt/hevo/Caddyfile`
- `deploy/deploy.sh` → `/opt/hevo/deploy.sh` (já vem com +x, confira depois do scp)

Crie `/opt/hevo/.env` a partir de `deploy/.env.example`, preenchendo os
valores reais (ver comentários no arquivo).

Primeiro `up` manual, pra não depender do pipeline logo de cara:

```bash
cd /opt/hevo
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com
docker compose pull
docker compose run --rm web python manage.py migrate --noinput
docker compose exec web python manage.py createsuperuser   # só na primeira vez
docker compose up -d
```

O Caddy provisiona o certificado TLS sozinho no primeiro boot, desde que o
DNS (passo 7) já esteja apontando pro IP e as portas 80/443 estejam
liberadas.

## 9. GitHub — secrets e environment

Em Settings → Secrets and variables → Actions:

- Secret de repositório: `AWS_ROLE_ARN` (do passo 2)

Em Settings → Environments, criar `production` com:

- `SSH_HOST` — Elastic IP da instância
- `SSH_USER` — `ec2-user`
- `SSH_KEY` — chave privada do key pair usado no `run-instances`

Recomendado marcar "Required reviewers" nela, pra exigir aprovação manual
antes de um deploy ir pro ar — não está configurado hoje.

## 10. Primeiro deploy automático

```bash
git push origin main   # builda, publica hevo:prod, reimplanta
```

Acompanhe em Actions → Deploy.

## 11. Rollback

A tag `hevo:prod` é mutável — cada deploy sobrescreve. Pra voltar uma
versão: Actions → Deploy → ache o run do commit anterior → "Re-run all
jobs". Isso rebuilda aquele commit e sobrescreve a tag de novo,
reimplantando a versão antiga.

## 12. E-mail (pendente)

`EMAIL_BACKEND` em produção é `smtp.EmailBackend`, mas o `deploy/.env.example`
deixa `EMAIL_HOST` em branco — sem configurar, cai no default `localhost:25`,
que não existe na instância. Isso hoje **não quebra nada** (o envio falha
silenciosamente, só loga um erro), mas também **não notifica ninguém** — por
exemplo, o e-mail de "atendimento humano solicitado" (`NotificationService.
notify_escalation`) não chega em lugar nenhum.

Pra funcionar de verdade, configure um SMTP real e preencha no `.env` do
servidor:

```
EMAIL_HOST=<host do provedor, ex: email-smtp.us-east-2.amazonaws.com>
EMAIL_PORT=587
EMAIL_HOST_USER=<usuário SMTP>
EMAIL_HOST_PASSWORD=<senha/token SMTP>
EMAIL_USE_TLS=True
```

Opções comuns: AWS SES (mesma região da infra, barato, mas sai do sandbox
exigindo verificação de domínio/e-mail antes de mandar pra destinatários
não verificados), SendGrid, Mailgun. Qualquer um funciona — só precisa de
credenciais SMTP válidas nesses quatro campos.

## Custos estimados (us-east-2)

| Item | Custo |
|---|---|
| EC2 t4g.micro | ~$6 |
| EBS 20GB | ~$2 |
| S3 (uso baixo) | ~$1 |
| ECR (uso baixo) | ~$1 |
| **Total** | **~$10/mês** |

## Upgrade futuro (não é o plano ativo hoje)

Se o volume de clientes reais justificar, os próximos degraus de robustez
seriam RDS Postgres gerenciado (backup automático, sem depender do volume
Docker) e uma instância maior (`t4g.small`+) com um ambiente `production`
protegido por "Required reviewers". Nenhum dos dois está sendo provisionado
agora — por enquanto é essa única instância mesmo.
