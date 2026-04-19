# llm_analyzer.py
import requests
from datetime import datetime, timedelta
from flask import current_app


class LLMAnalyzer:
    def __init__(self, model='deepseek-r1:8b', ollama_url='http://localhost:11434'):
        self.model = model
        self.ollama_url = ollama_url
        self.ollama_api_url = f"{ollama_url}/api/generate"

    def _get_db_models(self):
        """延迟导入避免循环依赖"""
        try:
            from app import db, AppLog, Alert
            return db, AppLog, Alert
        except Exception as e:
            print(f"[ERROR] 导入数据库模型失败: {e}")
            return None, None, None

    def _get_service(self, service_key):
        """获取服务信息"""
        try:
            from app import Service
            return Service.query.filter_by(service_key=service_key).first()
        except Exception as e:
            print(f"[ERROR] 获取服务信息失败: {e}")
            return None

    def _call_ollama(self, prompt):
        """调用本地 Ollama API"""
        try:
            response = requests.post(
                self.ollama_api_url,
                json={
                    'model': self.model,
                    'prompt': prompt,
                    'stream': False,
                    'options': {
                        'temperature': 0.3,
                        'num_predict': 2048
                    }
                },
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                print(f"Ollama API 错误: {response.status_code}")
                return None

        except Exception as e:
            print(f"Ollama 调用失败: {e}")
            return None

    def _build_prompt(self, logs, service_name, error_context):
        """构建提示词"""
        log_text = '\n'.join([f"[{log.get('level', 'INFO')}] {log.get('message', '')}" for log in logs[:20]])

        return f"""请分析以下{service_name}服务的日志，给出可能的故障原因和解决建议：

服务名: {service_name}
错误上下文: {error_context or '性能指标异常'}

日志内容:
{log_text}

请用中文简洁地回答：
1. 主要问题是什么？
2. 可能的原因（2-3点）
3. 建议的排查方向
"""

    def analyze_logs(self, logs, service_name, error_context=None):
        """分析日志并生成诊断"""
        if not logs:
            return f"[{service_name}] 没有日志数据，无法分析"

        prompt = self._build_prompt(logs, service_name, error_context)
        result = self._call_ollama(prompt)

        if result:
            return result
        else:
            raise Exception(f"Ollama 服务调用失败，请检查 Ollama 是否正常运行在 {self.ollama_url}")

    def analyze_from_db(self, service_key, alert_id=None, minutes=30):
        """
        从数据库获取日志并分析
        """
        try:
            # 使用 app.app_context() 确保应用上下文
            from app import app

            with app.app_context():
                db, AppLog, Alert = self._get_db_models()
                if db is None:
                    return "数据库连接失败", []

                # 获取最近 N 分钟的日志
                cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
                logs_query = AppLog.query.filter(
                    AppLog.service_key == service_key,
                    AppLog.timestamp >= cutoff_time
                ).order_by(AppLog.timestamp.desc()).limit(30).all()

                logs = [log.to_dict() for log in logs_query]

                # 获取服务信息
                service = self._get_service(service_key)
                service_name = service.service_name if service else service_key

                # 获取错误上下文
                error_context = None
                if alert_id:
                    alert = Alert.query.get(alert_id)
                    if alert:
                        error_context = f"{alert.metric_name} 异常，当前值: {alert.metric_value}"

                if not logs:
                    diagnosis = f"[{service_name}] 未找到相关日志，建议检查服务是否正常运行。"
                    return diagnosis, []

                diagnosis = self.analyze_logs(logs, service_name, error_context)

                if alert_id:
                    alert = Alert.query.get(alert_id)
                    if alert:
                        alert.llm_diagnosis = diagnosis
                        db.session.commit()

                return diagnosis, logs

        except Exception as e:
            print(f"[ERROR] analyze_from_db 失败: {e}")
            import traceback
            traceback.print_exc()
            return f"分析失败: {str(e)}", []

    def set_model(self, model_name):
        self.model = model_name
        print(f"已切换到模型: {model_name}")

    def list_models(self):
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [m['name'] for m in models]
            return []
        except Exception as e:
            print(f"获取模型列表失败: {e}")
            return []


# 创建全局实例
llm_analyzer = LLMAnalyzer(model='deepseek-r1:8b')