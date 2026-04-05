FROM python:3.11-slim

WORKDIR /app

# Instalar dependências de sistema (necessárias para compiladores C / PyMuPDF e requests)
RUN apt-get update && apt-get install -y \
  build-essential \
  gcc \
  curl \
  && rm -rf /var/lib/apt/lists/*

# Otimização de cache do Docker
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir --upgrade pip && \
  pip install --no-cache-dir -r requirements.txt

# Copiar o restante da aplicação
COPY . .

# Criar um usuário que não seja root (melhor prática de segurança)
RUN useradd -m appuser && \
  mkdir -p /app/data && \
  chown -R appuser:appuser /app

# Mudar o usuário e setar permissões
USER appuser

# Exposição e Variáveis
ENV PORT=2345 \
    APP_ENV=production \
    PYTHONUNBUFFERED=1

EXPOSE 2345

CMD ["gunicorn", "--bind", "0.0.0.0:2345", "--workers", "2", "--timeout", "120", "app:app"]
