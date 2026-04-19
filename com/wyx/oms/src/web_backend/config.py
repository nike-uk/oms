import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///ops_platform.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Prometheus配置
    PROMETHEUS_URL = os.environ.get('PROMETHEUS_URL', 'http://localhost:9090')

    # Elasticsearch配置（暂用Mock）
    ES_HOST = os.environ.get('ES_HOST', 'localhost')
    ES_PORT = os.environ.get('ES_PORT', 9200)

    # LLM配置（支持OpenAI或本地模型）
    LLM_API_URL = os.environ.get('LLM_API_URL', '')
    LLM_API_KEY = os.environ.get('LLM_API_KEY', '')
    LLM_MODEL = os.environ.get('LLM_MODEL', 'gpt-3.5-turbo')

    # 异常检测配置
    ANOMALY_DETECTION_WINDOW = 60  # 分钟
    ANOMALY_CONTAMINATION = 0.05  # 预期异常比例