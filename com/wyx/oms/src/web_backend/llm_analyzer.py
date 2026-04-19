import requests
import json
from config import Config


class LLMAnalyzer:
    def __init__(self):
        self.api_url = Config.LLM_API_URL
        self.api_key = Config.LLM_API_KEY
        self.model = Config.LLM_MODEL

    def analyze_logs(self, logs, service_name, error_context=None):
        """分析日志并生成诊断"""

        # 如果没有配置API，返回Mock结果
        if not self.api_key:
            return self._mock_analysis(logs, service_name)

        prompt = self._build_prompt(logs, service_name, error_context)

        try:
            response = requests.post(
                self.api_url,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.model,
                    'messages': [
                        {'role': 'system', 'content': '你是一个专业的运维专家，擅长分析系统日志并给出诊断建议。'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.3,
                    'max_tokens': 500
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                return self._mock_analysis(logs, service_name)

        except Exception as e:
            print(f"LLM调用失败: {e}")
            return self._mock_analysis(logs, service_name)

    def _build_prompt(self, logs, service_name, error_context):
        """构建提示词"""
        log_text = '\n'.join(logs[:20])  # 最多20条日志
        return f"""
请分析以下{service_name}服务的日志，给出可能的故障原因和解决建议：

服务名: {service_name}
错误上下文: {error_context or '性能指标异常'}

日志内容:
{log_text}

请用中文简洁地回答：
1. 主要问题是什么？
2. 可能的原因（2-3点）
3. 建议的排查方向
"""

    def _mock_analysis(self, logs, service_name):
        """Mock分析结果，用于演示"""
        mock_diagnoses = [
            "检测到大量数据库连接超时异常。可能原因：1) 数据库连接池配置过小 2) 数据库服务负载过高 3) 网络延迟。建议：检查连接池配置，查看数据库慢查询日志。",
            "发现内存使用持续增长，疑似内存泄漏。可能原因：1) 未正确释放对象引用 2) 缓存未设置过期时间。建议：使用内存分析工具检查堆内存。",
            "服务响应时间增加，伴随CPU使用率上升。可能原因：1) 业务流量突增 2) 存在慢接口或死循环。建议：检查QPS变化，分析接口耗时分布。",
            "日志中出现大量认证失败记录。可能原因：1) 凭证过期 2) 第三方认证服务异常。建议：检查认证配置和外部服务状态。"
        ]
        import random
        return random.choice(mock_diagnoses)