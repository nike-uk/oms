from sklearn.ensemble import IsolationForest
import numpy as np
from datetime import datetime, timedelta
from flask import current_app, has_app_context


class AnomalyDetector:
    def __init__(self, contamination=0.05, app=None):
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.is_fitted = False
        self.app = app  # 保存 Flask 应用实例

    def _get_app(self):
        """获取 Flask 应用实例"""
        if self.app:
            return self.app

        if has_app_context():
            return current_app._get_current_object()

        # 最后的备选方案：尝试导入 app
        try:
            from app import app
            return app
        except ImportError as e:
            raise RuntimeError(
                "无法获取 Flask 应用上下文。"
                "请确保在应用上下文中调用，或初始化时传入 app 实例。"
            ) from e

    def _get_db_models(self):
        """延迟导入避免循环依赖"""
        from app import db, Metric, Alert, Service
        return db, Metric, Alert, Service

    def prepare_data(self, service_key, metric_name, hours=1):
        """获取最近N小时的数据"""
        app = self._get_app()

        with app.app_context():
            db, Metric, Alert, Service = self._get_db_models()

            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            metrics = Metric.query.filter(
                Metric.service_key == service_key,
                Metric.metric_name == metric_name,
                Metric.timestamp >= cutoff_time
            ).order_by(Metric.timestamp.asc()).all()

            if len(metrics) < 10:
                return None, None

            values = np.array([float(m.metric_value) for m in metrics]).reshape(-1, 1)
            timestamps = [m.timestamp for m in metrics]
            return values, timestamps

    def fit(self, values):
        """训练模型"""
        if len(values) > 10:
            self.model.fit(values)
            self.is_fitted = True

    def detect(self, values):
        """检测异常，返回异常分数和标签"""
        if not self.is_fitted:
            self.fit(values)

        if len(values) == 0:
            return [], []

        predictions = self.model.predict(values)
        scores = self.model.score_samples(values)

        return predictions, scores

    def check_service_health(self, service_key, metrics_config):
        """检查服务健康状态，返回告警列表"""
        app = self._get_app()

        with app.app_context():
            db, Metric, Alert, Service = self._get_db_models()
            alerts = []

            for metric_config in metrics_config:
                metric_name = metric_config['name']

                values, timestamps = self.prepare_data(service_key, metric_name)
                if values is None or len(values) < 10:
                    continue

                predictions, scores = self.detect(values)

                # 检查最新数据点是否异常
                latest_prediction = predictions[-1]
                latest_score = scores[-1]
                latest_value = values[-1][0]

                if latest_prediction == -1:  # 异常
                    # 计算异常程度
                    mean_value = np.mean(values[:-1])
                    if mean_value > 0:
                        deviation = abs(latest_value - mean_value) / mean_value
                    else:
                        deviation = abs(latest_value - mean_value)

                    severity = 'warning'
                    if deviation > 0.5:
                        severity = 'critical'
                    elif deviation > 0.3:
                        severity = 'warning'
                    else:
                        severity = 'info'

                    # 获取服务名称
                    service = Service.query.filter_by(service_key=service_key).first()
                    service_name = service.service_name if service else service_key

                    # 计算异常分数 (0-1之间)
                    anomaly_score = min(0.95, deviation)

                    # 生成告警描述
                    metric_labels = {
                        'cpu_usage': 'CPU使用率',
                        'memory_usage': '内存使用率',
                        'request_latency': '请求延迟',
                        'error_rate': '错误率'
                    }
                    metric_label = metric_labels.get(metric_name, metric_name)

                    if metric_name in ['cpu_usage', 'memory_usage', 'error_rate']:
                        value_str = f"{latest_value:.1f}%"
                    elif metric_name == 'request_latency':
                        value_str = f"{latest_value:.0f}ms"
                    else:
                        value_str = f"{latest_value:.2f}"

                    alerts.append({
                        'service_key': service_key,
                        'service_name': service_name,
                        'metric_name': metric_name,
                        'metric_value': latest_value,
                        'anomaly_score': anomaly_score,
                        'severity': severity,
                        'title': f"{service_name} {metric_label} 异常",
                        'description': f"{metric_label}异常: 当前值{value_str}, 偏离正常值{deviation * 100:.1f}%",
                        'timestamp': timestamps[-1]
                    })

            return alerts

    def save_alerts_to_db(self, alerts):
        """将检测到的告警保存到数据库"""
        app = self._get_app()

        with app.app_context():
            db, Metric, Alert, Service = self._get_db_models()
            saved_alerts = []

            for alert_data in alerts:
                # 检查是否已存在相似的告警（避免重复）
                existing_alert = Alert.query.filter(
                    Alert.service_key == alert_data['service_key'],
                    Alert.metric_name == alert_data['metric_name'],
                    Alert.status == 'pending',
                    Alert.created_at >= datetime.utcnow() - timedelta(minutes=30)
                ).first()

                if existing_alert:
                    # 更新现有告警
                    existing_alert.metric_value = alert_data['metric_value']
                    existing_alert.anomaly_score = alert_data['anomaly_score']
                    existing_alert.severity = alert_data['severity']
                    existing_alert.description = alert_data['description']
                    saved_alerts.append(existing_alert)
                else:
                    # 创建新告警
                    alert = Alert(
                        service_key=alert_data['service_key'],
                        service_name=alert_data['service_name'],
                        metric_name=alert_data['metric_name'],
                        metric_value=alert_data['metric_value'],
                        anomaly_score=alert_data['anomaly_score'],
                        severity=alert_data['severity'],
                        title=alert_data.get('title', f"{alert_data['service_name']} {alert_data['metric_name']} 异常"),
                        description=alert_data['description'],
                        status='pending'
                    )
                    db.session.add(alert)
                    saved_alerts.append(alert)

            db.session.commit()
            return saved_alerts

    def detect_and_save(self, service_key=None, metrics_config=None):
        """执行检测并保存告警到数据库"""
        app = self._get_app()

        with app.app_context():
            db, Metric, Alert, Service = self._get_db_models()

            if metrics_config is None:
                metrics_config = [
                    {'name': 'cpu_usage'},
                    {'name': 'memory_usage'},
                    {'name': 'request_latency'},
                    {'name': 'error_rate'}
                ]

            if service_key:
                services = Service.query.filter_by(service_key=service_key).all()
            else:
                services = Service.query.all()

            all_alerts = []
            for service in services:
                try:
                    alerts = self.check_service_health(service.service_key, metrics_config)
                    if alerts:
                        saved = self.save_alerts_to_db(alerts)
                        all_alerts.extend(saved)
                except Exception as e:
                    print(f"检测服务 {service.service_key} 时出错: {e}")
                    continue

            return all_alerts

    def get_metric_history(self, service_key, metric_name, hours=24):
        """获取指标历史数据（用于前端图表）"""
        app = self._get_app()

        with app.app_context():
            db, Metric, Alert, Service = self._get_db_models()

            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            metrics = Metric.query.filter(
                Metric.service_key == service_key,
                Metric.metric_name == metric_name,
                Metric.timestamp >= cutoff_time
            ).order_by(Metric.timestamp.asc()).all()

            history = []
            for m in metrics:
                history.append({
                    'timestamp': m.timestamp.isoformat(),
                    'value': float(m.metric_value)
                })

            return history

    def reset_model(self):
        """重置模型（用于重新训练）"""
        self.model = IsolationForest(
            contamination=self.model.contamination,
            random_state=42,
            n_estimators=100
        )
        self.is_fitted = False
        print("模型已重置")


# 创建全局检测器实例的函数
def create_detector(app=None):
    """创建异常检测器实例"""
    return AnomalyDetector(app=app)


# 全局单例检测器
_detector_instance = None


def get_detector(app=None):
    """获取全局检测器单例"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = AnomalyDetector(app=app)
    elif app and _detector_instance.app is None:
        _detector_instance.app = app
    return _detector_instance