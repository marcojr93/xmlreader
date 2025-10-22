import pandas as pd
import hashlib
import re
import logging
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import os
import secrets
import json

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SecureDataProcessor:
    """
    Sistema de criptografia para dados sensíveis de Notas Fiscais
    com guardrails contra injection prompts e vazamentos de informação
    """
    
    def __init__(self, master_password: str = None):
        self.sensitive_fields = {
            'cnpj': ['Emitente CNPJ', 'Destinatário CNPJ', 'Transportadora CNPJ'],
            'cpf': ['Destinatário CPF'],
            'ie': ['Emitente IE', 'Destinatário IE'],
            'names': ['Emitente Nome', 'Destinatário Nome', 'Transportadora Nome', 'Emitente Fantasia'],
            'document_ids': ['Número NF', 'Chave NFe', 'Protocolo'],
            'address': ['Emitente CEP', 'Destinatário CEP', 'Emitente Município', 
                       'Destinatário Município', 'Emitente Logradouro', 'Destinatário Logradouro']
        }
        
        # Campos que NÃO devem ser criptografados (para uso pelo agente validador)
        self.public_fields = {
            'product_info': ['Produto', 'Descrição', 'NCM', 'CFOP', 'Unidade', 'Quantidade'],
            'tax_values': ['Valor Unitário', 'Valor Total', 'Base ICMS', 'Alíquota ICMS', 
                          'Valor ICMS', 'Base PIS', 'Alíquota PIS', 'Valor PIS',
                          'Base COFINS', 'Alíquota COFINS', 'Valor COFINS', 'Valor IPI',
                          'Base IPI', 'Alíquota IPI'],
            'operation_info': ['Natureza Operação', 'UF', 'Modelo', 'Série', 'Tipo NF', 'Finalidade'],
            'dates': ['Data Emissão', 'Data Saída/Entrada']
        }
        
        # Gerar ou carregar chave de criptografia
        self.encryption_key = self._generate_or_load_key(master_password)
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Contadores para auditoria
        self.encryption_stats = {
            'total_records': 0,
            'encrypted_fields': 0,
            'public_fields': 0,
            'blocked_injections': 0,
            'timestamp': datetime.now().isoformat()
        }

    def _generate_or_load_key(self, password: str = None) -> bytes:
        """Gera ou carrega chave de criptografia segura"""
        key_file = 'encryption.key'
        
        if os.path.exists(key_file):
            logger.info("Carregando chave de criptografia existente")
            with open(key_file, 'rb') as f:
                return f.read()
        
        # Gerar nova chave
        if password is None:
            password = secrets.token_urlsafe(32)
            logger.warning(f"Senha gerada automaticamente: {password}")
        
        # Derivar chave da senha usando PBKDF2
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        # Salvar chave (em produção, use um cofre de chaves)
        with open(key_file, 'wb') as f:
            f.write(key)
        
        logger.info("Nova chave de criptografia gerada e salva")
        return key

    def _detect_injection_patterns(self, text: str) -> bool:
        """
        Detecta padrões suspeitos que podem indicar tentativas de injection
        """
        if not isinstance(text, str):
            return False
            
        injection_patterns = [
            r'<script.*?>.*?</script>',  # XSS
            r'javascript:',  # JavaScript injection
            r'(union|select|insert|update|delete|drop)\s+',  # SQL injection básico
            r'(\|\||&&|\;)',  # Command injection
            r'(eval\(|exec\(|system\()',  # Code injection
            r'({{.*}}|\${.*})',  # Template injection
            r'(prompt\(|alert\(|confirm\()',  # Browser injection
            r'(import\s+|from\s+.*import)',  # Python import injection
        ]
        
        text_lower = text.lower()
        for pattern in injection_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL):
                logger.warning(f"Padrão de injection detectado: {pattern} em '{text[:50]}...'")
                self.encryption_stats['blocked_injections'] += 1
                return True
        
        return False

    def _sanitize_input(self, data: str) -> str:
        """
        Sanitiza entrada removendo caracteres perigosos
        """
        if not isinstance(data, str):
            return str(data)
        
        # Remove caracteres de controle e não-printáveis
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', data)
        
        # Remove tags HTML/XML suspeitas
        sanitized = re.sub(r'<[^>]*>', '', sanitized)
        
        # Limita tamanho do campo
        if len(sanitized) > 1000:
            sanitized = sanitized[:1000] + "..."
            logger.warning("Campo truncado por exceder limite de tamanho")
        
        return sanitized.strip()

    def _hash_for_indexing(self, data: str) -> str:
        """
        Cria hash para indexação sem revelar dados originais
        """
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def encrypt_sensitive_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Criptografa APENAS dados sensíveis (CNPJ, nomes de empresas, número NF)
        Mantém dados de produtos e impostos em texto claro para análise fiscal
        """
        logger.info(f"Iniciando criptografia seletiva de {len(df)} registros")
        encrypted_df = df.copy()
        self.encryption_stats['total_records'] = len(df)
        
        # Identificar campos sensíveis presentes no DataFrame
        sensitive_columns = []
        for category, fields in self.sensitive_fields.items():
            for field in fields:
                if field in df.columns:
                    sensitive_columns.append(field)
        
        # Identificar campos públicos (que não serão criptografados)
        public_columns = []
        for category, fields in self.public_fields.items():
            for field in fields:
                if field in df.columns:
                    public_columns.append(field)
        
        logger.info(f"Campos sensíveis (serão criptografados): {sensitive_columns}")
        logger.info(f"Campos públicos (mantidos em texto claro): {public_columns}")
        
        # Criptografar apenas campos sensíveis
        for column in sensitive_columns:
            logger.info(f"Criptografando campo sensível: {column}")
            encrypted_values = []
            hashed_indexes = []
            
            for index, value in df[column].items():
                # Converter para string se necessário
                str_value = str(value) if pd.notna(value) else ""
                
                # Detectar e bloquear injection attempts
                if self._detect_injection_patterns(str_value):
                    logger.error(f"Tentativa de injection bloqueada no campo {column}, registro {index}")
                    str_value = "[BLOCKED_CONTENT]"
                    self.encryption_stats['blocked_injections'] += 1
                
                # Sanitizar entrada
                sanitized_value = self._sanitize_input(str_value)
                
                if sanitized_value and sanitized_value != "0":
                    # Criptografar
                    encrypted_value = self.cipher_suite.encrypt(sanitized_value.encode())
                    encrypted_b64 = base64.b64encode(encrypted_value).decode()
                    encrypted_values.append(f"ENC:{encrypted_b64}")
                    
                    # Criar hash para indexação
                    hash_index = self._hash_for_indexing(sanitized_value)
                    hashed_indexes.append(hash_index)
                    
                    self.encryption_stats['encrypted_fields'] += 1
                else:
                    encrypted_values.append(str_value)
                    hashed_indexes.append("")
            
            # Substituir valores originais por criptografados
            encrypted_df[column] = encrypted_values
            encrypted_df[f"{column}_hash"] = hashed_indexes
        
        # Contar campos públicos mantidos
        self.encryption_stats['public_fields'] = len(public_columns)
        
        # Adicionar metadados de auditoria
        encrypted_df['_encrypted_timestamp'] = datetime.now().isoformat()
        encrypted_df['_encryption_version'] = "2.0_selective"
        encrypted_df['_public_fields_count'] = len(public_columns)
        encrypted_df['_encrypted_fields_count'] = len(sensitive_columns)
        
        logger.info(f"Criptografia concluída. {self.encryption_stats['encrypted_fields']} campos criptografados")
        return encrypted_df

    def decrypt_sensitive_data(self, encrypted_df: pd.DataFrame, fields_to_decrypt: list = None) -> pd.DataFrame:
        """
        Descriptografa dados sensíveis (usar apenas quando necessário)
        """
        if fields_to_decrypt is None:
            # Identificar todos os campos criptografados
            fields_to_decrypt = [col for col in encrypted_df.columns 
                               if encrypted_df[col].astype(str).str.startswith('ENC:').any()]
        
        logger.info(f"Descriptografando campos: {fields_to_decrypt}")
        decrypted_df = encrypted_df.copy()
        
        for column in fields_to_decrypt:
            if column in encrypted_df.columns:
                decrypted_values = []
                
                for value in encrypted_df[column]:
                    str_value = str(value)
                    if str_value.startswith('ENC:'):
                        try:
                            # Decodificar base64 e descriptografar
                            encrypted_data = base64.b64decode(str_value[4:])
                            decrypted_value = self.cipher_suite.decrypt(encrypted_data).decode()
                            decrypted_values.append(decrypted_value)
                        except Exception as e:
                            logger.error(f"Erro ao descriptografar {column}: {e}")
                            decrypted_values.append("[DECRYPT_ERROR]")
                    else:
                        decrypted_values.append(str_value)
                
                decrypted_df[column] = decrypted_values
        
        return decrypted_df

    def search_by_hash(self, encrypted_df: pd.DataFrame, field: str, search_value: str) -> pd.DataFrame:
        """
        Busca registros usando hash sem descriptografar
        """
        hash_column = f"{field}_hash"
        if hash_column not in encrypted_df.columns:
            logger.error(f"Campo hash {hash_column} não encontrado")
            return pd.DataFrame()
        
        search_hash = self._hash_for_indexing(search_value)
        results = encrypted_df[encrypted_df[hash_column] == search_hash]
        
        logger.info(f"Busca por hash encontrou {len(results)} registros")
        return results

    def get_encryption_stats(self) -> dict:
        """Retorna estatísticas de criptografia"""
        return self.encryption_stats.copy()

    def export_secure_data(self, encrypted_df: pd.DataFrame, filename: str = None):
        """
        Exporta dados criptografados com segurança
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"secure_nfe_data_{timestamp}.json"
        
        # Converter DataFrame para formato seguro
        secure_data = {
            'metadata': {
                'encryption_version': '2.0_selective',
                'timestamp': datetime.now().isoformat(),
                'total_records': len(encrypted_df),
                'encryption_stats': self.encryption_stats,
                'encryption_policy': 'selective_encryption_for_ai_analysis'
            },
            'data': encrypted_df.to_dict('records')
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(secure_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Dados seguros exportados para {filename}")
        return filename

# Função principal para demonstração
def main():
    """
    Demonstração do sistema de criptografia seletiva
    """
    # Dados de exemplo simulando extração de NF-e com mais campos
    sample_data = {
        # Campos sensíveis (serão criptografados)
        'Número NF': ['001', '002', '003'],
        'Emitente CNPJ': ['12.345.678/0001-90', '98.765.432/0001-10', '11.222.333/0001-44'],
        'Emitente Nome': ['Empresa ABC Ltda', 'Fornecedor XYZ S.A.', 'Distribuidor 123'],
        'Destinatário CNPJ': ['99.888.777/0001-66', '55.444.333/0001-22', '77.666.555/0001-88'],
        'Destinatário Nome': ['Cliente Final Ltda', 'Revendedor Beta', 'Comprador Gama'],
        
        # Campos públicos (mantidos em texto claro para análise fiscal)
        'Produto': ['Notebook Dell', 'Monitor Samsung', 'Teclado Logitech'],
        'NCM': ['84713012', '85285210', '84716060'],
        'CFOP': ['6102', '5102', '6109'],
        'Valor Unitário': ['1200.00', '800.00', '150.00'],
        'Alíquota ICMS': ['18%', '18%', '12%'],
        'Valor ICMS': ['216.00', '144.00', '18.00'],
        'Natureza Operação': ['Venda', 'Venda', 'Venda'],
        'Data Emissão': ['2025-10-20', '2025-10-21', '2025-10-22']
    }
    
    df = pd.DataFrame(sample_data)
    
    print("=== SISTEMA DE CRIPTOGRAFIA SELETIVA PARA ANÁLISE FISCAL ===\n")
    print("1. Dados originais:")
    print(df)
    print("\n" + "="*60 + "\n")
    
    # Inicializar sistema de criptografia
    crypto_system = SecureDataProcessor(master_password="minha_senha_super_secreta")
    
    # Criptografar dados sensíveis
    encrypted_df = crypto_system.encrypt_sensitive_data(df)
    
    print("2. Dados após criptografia:")
    print(encrypted_df[['Número NF', 'Emitente CNPJ', 'Emitente Nome', 'Valor NF', 'Data Emissão']])
    print("\n" + "="*60 + "\n")
    
    # Demonstrar busca por hash
    print("3. Busca segura por CNPJ usando hash:")
    search_results = crypto_system.search_by_hash(encrypted_df, 'Emitente CNPJ', '12.345.678/0001-90')
    print(f"Registros encontrados: {len(search_results)}")
    if not search_results.empty:
        print(search_results[['Número NF', 'Emitente CNPJ_hash', 'Data Emissão']])
    print("\n" + "="*60 + "\n")
    
    # Demonstrar descriptografia controlada
    print("4. Descriptografia controlada (apenas campos específicos):")
    decrypted_df = crypto_system.decrypt_sensitive_data(encrypted_df, ['Emitente Nome'])
    print(decrypted_df[['Número NF', 'Emitente Nome', 'Data Emissão']])
    print("\n" + "="*60 + "\n")
    
    # Estatísticas de segurança
    print("5. Estatísticas de criptografia:")
    stats = crypto_system.get_encryption_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print("\n" + "="*60 + "\n")
    
    # Exportar dados seguros
    secure_file = crypto_system.export_secure_data(encrypted_df)
    print(f"6. Dados exportados com segurança para: {secure_file}")
    
    # Teste de proteção contra injection
    print("\n7. Teste de proteção contra injection:")
    malicious_data = {
        'Número NF': ['<script>alert("xss")</script>'],
        'Emitente Nome': ['Empresa; DROP TABLE users; --'],
        'Produto': ['Notebook Dell'],  # Campo público, não criptografado
        'NCM': ['84713012']  # Campo público, não criptografado
    }
    malicious_df = pd.DataFrame(malicious_data)
    
    print("Dados maliciosos detectados e bloqueados:")
    protected_df = crypto_system.encrypt_sensitive_data(malicious_df)
    print(protected_df)
    print("\nObservação: Campos sensíveis com conteúdo malicioso foram bloqueados,")
    print("mas campos públicos para análise fiscal permanecem acessíveis.")

if __name__ == "__main__":
    main()