from sklearn.ensemble import IsolationForest
import numpy as np
from datetime import datetime, timedelta
from models import MetricSnapshot, db


class AnomalyDetector:
    def __init__(self, contamination=0.05):
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.is_fitted = False

    def prepare_data(self, service_name, metric_name, hours=1):
        """获取最近N小时的数据"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        snapshots = MetricSnapshot.query.filter(
            MetricSnapshot.service_name == service_name,
            MetricSnapshot.metric_name == metric_name,
            MetricSnapshot.timestamp >= cutoff_time
        ).order_by(MetricSnapshot.timestamp.asc()).all()

        if len(snapshots) < 10:
            return None, None

        values = np.array([s.metric_value for s in snapshots]).reshape(-1, 1)
        timestamps = [s.timestamp for s in snapshots]
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

        # 转换: -1表示异常, 1表示正常
        # 分数越低越异常
        return predictions, scores

    def check_service_health(self, service_name, metrics_config):
        """检查服务健康状态，返回告警列表"""
        alerts = []

        for metric_config in metrics_config:
            metric_name = metric_config['name']
            threshold_multiplier = metric_config.get('threshold', 2.0)

            values, timestamps = self.prepare_data(service_name, metric_name)
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
                deviation = abs(latest_value - mean_value) / mean_value if mean_value > 0 else 0

                severity = 'warning'
                if deviation > 0.5:
                    severity = 'critical'
                elif deviation > 0.3:
                    severity = 'warning'
                else:
                    severity = 'info'

                alerts.append({
                    'service_name': service_name,
                    'metric_name': metric_name,
                    'metric_value': latest_value,
                    'anomaly_score': float(abs(latest_score)),
                    'severity': severity,
                    'description': f'{metric_name}异常: 当前值{latest_value:.2f}, 偏离正常值{deviation * 100:.1f}%',
                    'timestamp': timestamps[-1]
                })

        return alerts