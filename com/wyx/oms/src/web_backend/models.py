from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()


class Alert(db.Model):
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    service_name = db.Column(db.String(100), nullable=False)
    metric_name = db.Column(db.String(100), nullable=False)
    metric_value = db.Column(db.Float)
    anomaly_score = db.Column(db.Float)
    severity = db.Column(db.String(20), default='warning')  # info, warning, critical
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, resolved
    description = db.Column(db.Text)
    llm_diagnosis = db.Column(db.Text)  # LLM生成的诊断
    related_logs = db.Column(db.Text)  # JSON格式的相关日志
    affected_services = db.Column(db.Text)  # JSON格式的影响服务
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'service_name': self.service_name,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'anomaly_score': self.anomaly_score,
            'severity': self.severity,
            'status': self.status,
            'description': self.description,
            'llm_diagnosis': self.llm_diagnosis,
            'related_logs': json.loads(self.related_logs) if self.related_logs else [],
            'affected_services': json.loads(self.affected_services) if self.affected_services else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


class MetricSnapshot(db.Model):
    __tablename__ = 'metric_snapshots'

    id = db.Column(db.Integer, primary_key=True)
    service_name = db.Column(db.String(100), nullable=False)
    metric_name = db.Column(db.String(100), nullable=False)
    metric_value = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'service_name': self.service_name,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'timestamp': self.timestamp.isoformat()
        }