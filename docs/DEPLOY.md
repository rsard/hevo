# Deploy na AWS

Runbook manual (sem Terraform) pra provisionar dev e prod e ligar o deploy
automático via GitHub Actions. Execute uma vez por ambiente; depois disso,
todo push em `develop` (dev) ou `main` (prod) builda a imagem e reimplanta
sozinho.

Arquitetura: 1 instância EC2 por ambiente rodando Docker Compose (web +
celery worker + celery beat + redis + Caddy pra HTTPS). Prod usa RDS Postgres
gerenciado; dev roda Postgres em container pra economizar. Domínios:
`app.hevo.ia.br` (prod) e `dev.hevo.ia.br` (dev).

Substitua `<ACCOUNT_ID>` pelo seu AWS Account ID em todos os comandos abaixo.
Região: `us-east-2`.

**Fase atual: só dev.** Os passos marcados "(prod)" ficam pra depois — não
provisionar RDS/EC2 de prod nem mergear `develop` em `main` ainda, pra não
gerar custo de prod antes da hora.

## 1. ECR — repositório de imagens

```bash
aws ecr create-repository --repository-name hevo --region us-east-2
```

## 2. IAM role pro GitHub Actions (OIDC, sem chave fixa)

Criar o provider OIDC do GitHub (uma vez por conta AWS):

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea
```

Trust policy (`trust.json`) — restringe a role ao repo `rsard/hevo`:

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
        "token.actions.githubusercontent.com:sub": "repo:rsard/hevo:ref:refs/heads/*"
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
vai virar o secret `AWS_ROLE_ARN` no GitHub (passo 12).

## 3. IAM role pra EC2 puxar do ECR

As instâncias usam uma instance profile em vez de chaves fixas:

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

Ambos os buckets já existem (`hevo-develop` e `hevo-prod`), nada a criar
aqui. Só confirme que o IAM user cujas chaves vão pro `.env` tem acesso aos
dois — senão, adicione `hevo-prod` à policy dele quando chegar a hora do
prod.

## 5. Security groups

```bash
aws ec2 create-security-group --group-name hevo-dev-sg \
  --description "Hevo dev" --vpc-id <VPC_ID>

# 80/443 abertos, 22 só do seu IP
aws ec2 authorize-security-group-ingress --group-id <DEV_SG_ID> \
  --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id <DEV_SG_ID> \
  --protocol tcp --port 443 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id <DEV_SG_ID> \
  --protocol tcp --port 22 --cidr <SEU_IP>/32
```

(prod, mais tarde) mesma coisa com `hevo-prod-sg`, mais uma
`hevo-prod-rds-sg` liberando 5432 só a partir da `hevo-prod-sg`:

```bash
aws ec2 create-security-group --group-name hevo-prod-sg \
  --description "Hevo prod" --vpc-id <VPC_ID>
aws ec2 create-security-group --group-name hevo-prod-rds-sg \
  --description "Hevo prod RDS" --vpc-id <VPC_ID>
aws ec2 authorize-security-group-ingress --group-id <RDS_SG_ID> \
  --protocol tcp --port 5432 --source-group <PROD_SG_ID>
```

## 6. Instância EC2 (dev)

Amazon Linux 2023 (arm64), Docker + Compose instalados via user-data.
`t4g.nano` (2 vCPU, 0.5GB RAM) — o mínimo possível. Com Django + Redis +
2 processos Celery nesse pouco de RAM, adicione um swapfile no user-data
pra evitar OOM kill em picos, já que 512MB é justo:

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

# swap — t4g.nano só tem 512MB de RAM
fallocate -l 1G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

```bash
aws ec2 run-instances --image-id <AL2023_ARM64_AMI_ID> \
  --instance-type t4g.nano --key-name <SEU_KEY_PAIR> \
  --security-group-ids <DEV_SG_ID> \
  --iam-instance-profile Name=hevo-ec2-ecr-pull \
  --user-data file://user-data.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=hevo-dev}]'
```

Aloque um Elastic IP (`aws ec2 allocate-address` + `associate-address`) pra
o IP não mudar em um restart.

(prod, mais tarde) mesma instância, trocando `<DEV_SG_ID>` por
`<PROD_SG_ID>` e o tag `hevo-dev` por `hevo-prod`. Comece também em
`t4g.small` ou maior — prod atende clientes reais, `nano` é aceitável só
pra dev. Redimensiona depois se precisar (`stop` → `modify-instance-attribute`
→ `start`), sem tocar em mais nada.

## 7. RDS (prod, mais tarde)

```bash
aws rds create-db-instance \
  --db-instance-identifier hevo-prod \
  --engine postgres --engine-version 16 \
  --db-instance-class db.t4g.micro \
  --allocated-storage 20 --storage-type gp3 \
  --master-username hevo --master-user-password <SENHA_FORTE> \
  --db-name hevo \
  --vpc-security-group-ids <RDS_SG_ID> \
  --no-multi-az --no-publicly-accessible \
  --backup-retention-period 7
```

Anote o endpoint (`aws rds describe-db-instances`) pro `DATABASE_URL` do
`.env` de prod.

## 8. DNS

`hevo.ia.br` provavelmente está no Registro.br (não Route53) — não é preciso
criar hosted zone paga. Onde o DNS estiver hoje, crie:

- `A dev.hevo.ia.br` → Elastic IP da instância dev
- (prod, mais tarde) `A app.hevo.ia.br` → Elastic IP da instância prod

## 9. Configurar o servidor (dev)

Via SSH:

```bash
ssh ec2-user@<IP>
sudo mkdir -p /opt/hevo && sudo chown ec2-user:ec2-user /opt/hevo
```

Copie do repo pra `/opt/hevo/` (via `scp` local):

- `deploy/docker-compose.dev.yml` → `/opt/hevo/docker-compose.yml`
- `deploy/Caddyfile` → `/opt/hevo/Caddyfile`
- `deploy/deploy.sh` → `/opt/hevo/deploy.sh` (já vem com +x, confira depois do scp)

Crie `/opt/hevo/.env` a partir de `deploy/.env.example`, preenchendo os
valores reais de dev (ver comentários no arquivo).

(prod, mais tarde) mesma coisa, usando `deploy/docker-compose.prod.yml`.

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
DNS (passo 8) já esteja apontando pro IP e as portas 80/443 estejam
liberadas.

## 10. GitHub — secrets e environments

Em Settings → Secrets and variables → Actions:

- Secret de repositório: `AWS_ROLE_ARN` (do passo 2)

Em Settings → Environments, criar `development` com:

- `SSH_HOST` — Elastic IP da instância dev
- `SSH_USER` — `ec2-user`
- `SSH_KEY` — chave privada do key pair usado no `run-instances`

(prod, mais tarde) criar também `production` com os mesmos três secrets
apontando pra instância prod. Recomendado marcar "Required reviewers" nela,
pra exigir aprovação manual antes do deploy ir pro ar.

## 11. Primeiro deploy automático

```bash
git push origin develop   # builda, publica hevo:dev, reimplanta dev
```

Acompanhe em Actions → Deploy. Não dar push em `main` ainda — isso fica pra
quando decidirmos subir prod.

## 12. Rollback

As tags `hevo:dev`/`hevo:prod` são mutáveis — cada deploy sobrescreve. Pra
voltar uma versão: Actions → Deploy → ache o run do commit anterior → "Re-run
all jobs". Isso rebuilda aquele commit e sobrescreve a tag de novo,
reimplantando a versão antiga.

## Custos estimados (us-east-2)

Fase atual — só dev:

| Item | Dev |
|---|---|
| EC2 t4g.nano | ~$3 |
| EBS 20GB | ~$2 |
| S3 (uso baixo) | ~$1 |
| ECR (uso baixo) | ~$1 |
| **Total** | **~$7/mês** |

Quando prod entrar (t4g.small + RDS db.t4g.micro): mais ~$30-33/mês. Sem
custo de Route53 (DNS fica no Registro.br) nem de domínio novo.

`t4g.nano` tem só 512MB de RAM — se o Django/Celery começarem a OOM mesmo
com swap, o próximo degrau é `t4g.micro` (1GB, ~$6/mês) antes de ir pro
`small`.
