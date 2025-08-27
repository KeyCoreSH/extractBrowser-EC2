#!/usr/bin/env python3
"""
Módulo de gerenciamento S3
Funções para upload, download e gerenciamento de arquivos no S3
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class S3Manager:
    """Gerenciador de operações S3"""
    
    def __init__(self, bucket_name: str, region: str = 'us-east-2'):
        self.bucket_name = bucket_name
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        logger.info(f"🪣 S3Manager inicializado - Bucket: {bucket_name}, Região: {region}")
    
    def test_connection(self) -> bool:
        """Testa conexão com S3 e bucket"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"✅ Conexão S3 OK - Bucket {self.bucket_name} acessível")
            return True
        except ClientError as e:
            logger.error(f"❌ Erro conexão S3: {e}")
            return False
    
    def create_bucket_if_not_exists(self) -> bool:
        """Cria bucket se não existir"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"ℹ️ Bucket {self.bucket_name} já existe")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                try:
                    if self.region == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )
                    logger.info(f"✅ Bucket {self.bucket_name} criado com sucesso")
                    return True
                except ClientError as create_error:
                    logger.error(f"❌ Erro ao criar bucket: {create_error}")
                    return False
            else:
                logger.error(f"❌ Erro ao verificar bucket: {e}")
                return False
    
    def upload_file(self, file_content: bytes, filename: str, folder: str = "", 
                   content_type: str = "application/octet-stream") -> Optional[str]:
        """
        Upload de arquivo para S3
        
        Args:
            file_content: Conteúdo do arquivo em bytes
            filename: Nome do arquivo
            folder: Pasta no S3 (opcional)
            content_type: Tipo MIME do arquivo
        
        Returns:
            Chave S3 do arquivo ou None se falhar
        """
        try:
            # Gerar chave única
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            
            if folder:
                s3_key = f"{folder}/{timestamp}_{unique_id}_{filename}"
            else:
                s3_key = f"{timestamp}_{unique_id}_{filename}"
            
            logger.info(f"📤 Enviando arquivo para S3 - Chave: {s3_key}, Tamanho: {len(file_content)} bytes")
            
            # Upload para S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                ServerSideEncryption='AES256'  # Criptografia simples
            )
            
            logger.info(f"✅ Upload concluído - S3 Key: {s3_key}")
            return s3_key
            
        except ClientError as e:
            logger.error(f"❌ Erro no upload S3: {e}")
            return None
    
    def download_file(self, s3_key: str) -> Optional[bytes]:
        """
        Download de arquivo do S3
        
        Args:
            s3_key: Chave do arquivo no S3
        
        Returns:
            Conteúdo do arquivo em bytes ou None se falhar
        """
        try:
            logger.info(f"📥 Baixando arquivo do S3 - Chave: {s3_key}")
            
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            file_content = response['Body'].read()
            
            logger.info(f"✅ Download concluído - {len(file_content)} bytes")
            return file_content
            
        except ClientError as e:
            logger.error(f"❌ Erro no download S3: {e}")
            return None
    
    def get_file_url(self, s3_key: str, expires_in: int = 3600) -> Optional[str]:
        """
        Gera URL assinada para acesso temporário
        
        Args:
            s3_key: Chave do arquivo no S3
            expires_in: Tempo de expiração em segundos (padrão: 1 hora)
        
        Returns:
            URL assinada ou None se falhar
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expires_in
            )
            logger.info(f"🔗 URL gerada para {s3_key} (expira em {expires_in}s)")
            return url
        except ClientError as e:
            logger.error(f"❌ Erro ao gerar URL: {e}")
            return None
    
    def get_public_url(self, s3_key: str) -> str:
        """
        Gera URL pública para arquivo (requer bucket público)
        
        Args:
            s3_key: Chave do arquivo no S3
        
        Returns:
            URL pública
        """
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
    
    def delete_file(self, s3_key: str) -> bool:
        """
        Remove arquivo do S3
        
        Args:
            s3_key: Chave do arquivo no S3
        
        Returns:
            True se removido com sucesso
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"🗑️ Arquivo removido: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"❌ Erro ao remover arquivo: {e}")
            return False
    
    def list_files(self, prefix: str = "", max_keys: int = 100) -> list:
        """
        Lista arquivos no bucket
        
        Args:
            prefix: Prefixo para filtrar arquivos
            max_keys: Máximo de arquivos a retornar
        
        Returns:
            Lista de arquivos
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'modified': obj['LastModified'].isoformat(),
                        'etag': obj['ETag'].strip('"')
                    })
            
            logger.info(f"📋 Listados {len(files)} arquivos com prefixo '{prefix}'")
            return files
            
        except ClientError as e:
            logger.error(f"❌ Erro ao listar arquivos: {e}")
            return []

# Função de teste
def test_s3_manager():
    """Testa funcionalidades do S3Manager"""
    try:
        # Configurar logging
        logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
        
        # Inicializar manager
        bucket_name = "extractbrowser-ec2-test"
        s3_manager = S3Manager(bucket_name)
        
        print("🧪 Testando S3Manager...")
        
        # Testar conexão
        print("1. Testando conexão...")
        if not s3_manager.test_connection():
            print("❌ Falha na conexão - criando bucket...")
            if not s3_manager.create_bucket_if_not_exists():
                print("❌ Não foi possível criar bucket")
                return False
        
        # Testar upload
        print("2. Testando upload...")
        test_content = b"Teste de conteudo para S3"
        s3_key = s3_manager.upload_file(
            test_content, 
            "test.txt", 
            folder="tests",
            content_type="text/plain"
        )
        
        if not s3_key:
            print("❌ Falha no upload")
            return False
        
        # Testar download
        print("3. Testando download...")
        downloaded_content = s3_manager.download_file(s3_key)
        if downloaded_content != test_content:
            print("❌ Conteúdo baixado não confere")
            return False
        
        # Testar URL
        print("4. Testando geração de URL...")
        url = s3_manager.get_file_url(s3_key)
        if not url:
            print("❌ Falha na geração de URL")
            return False
        
        # Testar listagem
        print("5. Testando listagem...")
        files = s3_manager.list_files("tests/")
        if len(files) == 0:
            print("❌ Nenhum arquivo listado")
            return False
        
        # Limpar teste
        print("6. Limpando teste...")
        s3_manager.delete_file(s3_key)
        
        print("✅ Todos os testes passaram!")
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

if __name__ == "__main__":
    test_s3_manager()
