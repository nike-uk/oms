from datetime import datetime, timedelta
import random
import json


class MockDataGenerator:
    """生成Mock数据用于演示"""

    SERVICES = ['api-gateway', 'user-service', 'order-service', 'payment-service', 'inventory-service']
    METRICS = ['cpu_usage', 'memory_usage', 'request_latency', 'error_rate']

    @classmethod
    def generate_topology(cls):
        """生成服务拓扑数据"""
        nodes = []
        edges = []

        for i, service in enumerate(cls.SERVICES):
            nodes.append({
                'id': service,
                'name': service,
                'status': random.choice(['healthy', 'warning', 'critical']),
                'category': 0 if i == 0 else 1
            })

        # 定义依赖关系
        dependencies = [
            ('api-gateway', 'user-service'),
            ('api-gateway', 'order-service'),
            ('api-gateway', 'payment-service'),
            ('order-service', 'user-service'),
            ('order-service', 'inventory-service'),
            ('payment-service', 'user-service'),
        ]

        for source, target in dependencies:
            edges.append({
                'source': source,
                'target': target,
                'label': 'calls'
            })

        return {'nodes': nodes, 'edges': edges}

    @classmethod
    def generate_dashboard_data(cls):
        """生成仪表盘数据"""
        return {
            'summary': {
                'total_services': 5,
                'healthy_services': 3,
                'warning_services': 1,
                'critical_services': 1,
                'pending_alerts': 4,
                'confirmed_alerts': 2
            },
            'alert_trends': cls._generate_alert_trends(),
            'service_health': cls._generate_service_health(),
            'recent_alerts': cls._generate_recent_alerts(5)
        }

    @classmethod
    def _generate_alert_trends(cls):
        """生成最近7天的告警趋势"""
        trends = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=6 - i)).strftime('%m-%d')
            trends.append({
                'date': date,
                'critical': random.randint(0, 5),
                'warning': random.randint(2, 10),
                'info': random.randint(5, 15)
            })
        return trends

    @classmethod
    def _generate_service_health(cls):
        """生成服务健康状态"""
        health_data = []
        for service in cls.SERVICES:
            health_data.append({
                'name': service,
                'status': random.choice(['healthy', 'warning', 'critical']),
                'cpu': round(random.uniform(10, 90), 1),
                'memory': round(random.uniform(20, 85), 1),
                'latency': round(random.uniform(10, 500), 0)
            })
        return health_data

    @classmethod
    def _generate_recent_alerts(cls, count):
        """生成最近的告警"""
        alerts = []
        for i in range(count):
            service = random.choice(cls.SERVICES)
            metric = random.choice(cls.METRICS)
            minutes_ago = random.randint(5, 120)

            alerts.append({
                'id': i + 1,
                'service_name': service,
                'metric_name': metric,
                'severity': random.choice(['critical', 'warning', 'info']),
                'status': random.choice(['pending', 'confirmed']),
                'description': f'{service} {metric} 出现异常',
                'created_at': (datetime.now() - timedelta(minutes=minutes_ago)).isoformat()
            })
        return alerts

    @classmethod
    def generate_metric_history(cls, service_name, metric_name, hours=24):
        """生成指标历史数据"""
        data = []
        now = datetime.now()

        for i in range(hours * 60):
            timestamp = now - timedelta(minutes=hours * 60 - i)

            if metric_name == 'cpu_usage':
                base_value = 30 + random.uniform(-10, 20)
                # 模拟一些异常峰值
                if random.random() < 0.05:
                    base_value = 85 + random.uniform(0, 15)
            elif metric_name == 'memory_usage':
                base_value = 50 + random.uniform(-10, 15)
            elif metric_name == 'request_latency':
                base_value = 100 + random.uniform(-30, 50)
                if random.random() < 0.03:
                    base_value = 800 + random.uniform(0, 500)
            else:  # error_rate
                base_value = 1 + random.uniform(-0.5, 1)
                if random.random() < 0.02:
                    base_value = 15 + random.uniform(0, 10)

            data.append({
                'timestamp': timestamp.isoformat(),
                'value': round(max(0, base_value), 2)
            })

        return data

    @classmethod
    def generate_related_logs(cls, service_name, count=10):
        """生成相关日志"""
        log_templates = {
            'api-gateway': [
                'ERROR: upstream connect error or disconnect/reset before headers',
                'WARN: request timeout after 30s, client ip: 10.0.1.23',
                'INFO: rate limit exceeded for user 12345',
                'ERROR: no healthy upstream for service user-service',
            ],
            'user-service': [
                'ERROR: database connection pool exhausted',
                'WARN: slow query detected: SELECT * FROM users (took 5.2s)',
                'ERROR: failed to acquire connection after 10000ms',
                'INFO: cache miss for user:9876, fallback to db',
            ],
            'order-service': [
                'ERROR: transaction rollback: inventory service unavailable',
                'WARN: circuit breaker opened for payment-service',
                'ERROR: deadlock detected in order processing',
                'INFO: order creation latency exceeded threshold',
            ],
            'payment-service': [
                'ERROR: third-party payment gateway timeout',
                'WARN: duplicate transaction detected',
                'ERROR: failed to verify payment signature',
                'INFO: payment processing queued for retry',
            ],
            'inventory-service': [
                'ERROR: stock update conflict for item SKU12345',
                'WARN: low stock alert for product 67890',
                'ERROR: redis connection lost, fallback to db',
                'INFO: batch update completed with 2 failures',
            ]
        }

        templates = log_templates.get(service_name, log_templates['api-gateway'])
        logs = []
        now = datetime.now()

        for i in range(count):
            logs.append({
                'timestamp': (now - timedelta(minutes=random.randint(1, 30))).isoformat(),
                'level': random.choice(['ERROR', 'WARN', 'INFO']),
                'message': random.choice(templates)
            })

        return sorted(logs, key=lambda x: x['timestamp'], reverse=True)