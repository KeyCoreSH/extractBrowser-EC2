#!/bin/bash
# Deploy script para ExtractBrowser EC2

set -e

echo "🚀 Deploy ExtractBrowser EC2"
echo "================================"

# Configurações
APP_DIR="/opt/extractbrowser"
SERVICE_NAME="extractbrowser"
BUCKET_NAME="extractbrowser-ec2-documents"
REGION="us-east-2"
PORT="2345"

# Função para instalar dependências do sistema
install_system_deps() {
    echo "📦 Instalando dependências do sistema..."
    
    if command -v yum &> /dev/null; then
        # Amazon Linux / RHEL
        sudo yum update -y
        sudo yum install -y python3 python3-pip python3-devel gcc nginx
        sudo amazon-linux-extras install -y nginx1
    elif command -v apt &> /dev/null; then
        # Ubuntu / Debian
        sudo apt update
        sudo apt install -y python3 python3-pip python3-dev gcc nginx
    else
        echo "❌ Sistema operacional não suportado"
        exit 1
    fi
    
    echo "✅ Dependências do sistema instaladas"
}

# Função para configurar aplicação
setup_application() {
    echo "🏗️ Configurando aplicação..."
    
    # Criar diretório da aplicação
    sudo mkdir -p $APP_DIR
    sudo chown ec2-user:ec2-user $APP_DIR
    
    # Copiar arquivos
    cp -r . $APP_DIR/
    cd $APP_DIR
    
    # Criar ambiente virtual
    python3 -m venv venv
    source venv/bin/activate
    
    # Instalar dependências Python
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo "✅ Aplicação configurada"
}

# Função para criar serviço systemd
create_systemd_service() {
    echo "⚙️ Criando serviço systemd..."
    
    sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=ExtractBrowser EC2 Document Service
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
Environment=S3_BUCKET=$BUCKET_NAME
Environment=AWS_REGION=$REGION
Environment=PORT=$PORT
ExecStart=$APP_DIR/venv/bin/gunicorn --bind 0.0.0.0:$PORT --workers 2 app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
    
    # Recarregar systemd e habilitar serviço
    sudo systemctl daemon-reload
    sudo systemctl enable $SERVICE_NAME
    
    echo "✅ Serviço systemd criado"
}

# Função para configurar Nginx
setup_nginx() {
    echo "🌐 Configurando Nginx..."
    
    sudo tee /etc/nginx/sites-available/extractbrowser > /dev/null <<EOF
server {
    listen 80;
    server_name _;
    
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://localhost:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # CORS headers
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Origin, Content-Type, Accept, Authorization" always;
        
        # Handle preflight
        if (\$request_method = OPTIONS) {
            return 204;
        }
    }
}
EOF
    
    # Habilitar site (Ubuntu) ou criar symlink
    if [ -d "/etc/nginx/sites-enabled" ]; then
        sudo ln -sf /etc/nginx/sites-available/extractbrowser /etc/nginx/sites-enabled/
        sudo rm -f /etc/nginx/sites-enabled/default
    else
        # Amazon Linux - editar nginx.conf diretamente
        sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup
        sudo sed -i '/server {/,$d' /etc/nginx/nginx.conf
        sudo cat /etc/nginx/sites-available/extractbrowser >> /etc/nginx/nginx.conf
        echo "}" | sudo tee -a /etc/nginx/nginx.conf
    fi
    
    # Testar configuração e reiniciar
    sudo nginx -t
    sudo systemctl enable nginx
    sudo systemctl restart nginx
    
    echo "✅ Nginx configurado"
}

# Função para criar bucket S3
setup_s3_bucket() {
    echo "🪣 Configurando bucket S3..."
    
    # Verificar se AWS CLI está configurado
    if ! aws sts get-caller-identity &> /dev/null; then
        echo "❌ AWS CLI não configurado ou sem permissões"
        echo "Configure com: aws configure"
        return 1
    fi
    
    # Criar bucket se não existir
    if ! aws s3 ls s3://$BUCKET_NAME &> /dev/null; then
        aws s3 mb s3://$BUCKET_NAME --region $REGION
        echo "✅ Bucket $BUCKET_NAME criado"
    else
        echo "ℹ️ Bucket $BUCKET_NAME já existe"
    fi
    
    # Configurar CORS
    aws s3api put-bucket-cors --bucket $BUCKET_NAME --cors-configuration '{
        "CORSRules": [
            {
                "AllowedHeaders": ["*"],
                "AllowedMethods": ["GET", "POST", "PUT"],
                "AllowedOrigins": ["*"],
                "ExposeHeaders": ["ETag"],
                "MaxAgeSeconds": 3000
            }
        ]
    }'
    
    echo "✅ CORS configurado no bucket"
}

# Função principal
main() {
    echo "Iniciando deploy em $(date)"
    
    # Verificar se está rodando como root (não deve)
    if [ "$EUID" -eq 0 ]; then
        echo "❌ Não execute este script como root"
        echo "Use: bash deploy.sh"
        exit 1
    fi
    
    # Executar etapas
    install_system_deps
    setup_application
    create_systemd_service
    setup_nginx
    setup_s3_bucket
    
    # Iniciar serviços
    echo "🚀 Iniciando serviços..."
    sudo systemctl start $SERVICE_NAME
    sudo systemctl status $SERVICE_NAME --no-pager
    
    echo ""
    echo "✅ Deploy concluído!"
    echo "🌐 Acesse: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
    echo "📊 Status: sudo systemctl status $SERVICE_NAME"
    echo "📋 Logs: sudo journalctl -u $SERVICE_NAME -f"
    echo "🔧 Porta interna: $PORT"
}

# Executar se chamado diretamente
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
