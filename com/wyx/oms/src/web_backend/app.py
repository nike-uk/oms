from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from anomaly_detector import get_detector, current_app
import hashlib
import os

detector = None

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# ========== MySQL 数据库配置 ==========
DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = '123456'  # 改成你的 MySQL 密码
DB_NAME = 'ops_platform'

app.config[
    'SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False

db = SQLAlchemy(app)
CORS(app, origins=['http://localhost:3000', 'http://127.0.0.1:3000'], supports_credentials=True)

# ========== Token 管理 ==========
user_sessions = {}


def init_detector(app):
    """初始化异常检测器"""
    global detector
    detector = get_detector(app)
    return detector


def generate_token(username):
    import base64
    import time
    token_str = f"{username}:{time.time()}"
    return base64.b64encode(token_str.encode()).decode()


def verify_token(token):
    import base64
    try:
        token_str = base64.b64decode(token.encode()).decode()
        username = token_str.split(':')[0]
        return username
    except:
        return None


def get_current_user():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    token = auth_header.replace('Bearer ', '')
    username = verify_token(token)
    if not username:
        return None
    return User.query.filter_by(username=username, status=1).first()


# ========== 数据模型定义 ==========

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(50))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    avatar = db.Column(db.String(500))
    role = db.Column(db.Enum('admin', 'user'), default='user')
    status = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'avatar': self.avatar,
            'role': self.role,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Service(db.Model):
    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    service_key = db.Column(db.String(100), nullable=False, unique=True)
    service_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    host = db.Column(db.String(100))
    port = db.Column(db.Integer)
    status = db.Column(db.Enum('healthy', 'warning', 'critical', 'unknown'), default='unknown')
    tags = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'service_key': self.service_key,
            'service_name': self.service_name,
            'description': self.description,
            'status': self.status
        }


class ServiceDependency(db.Model):
    __tablename__ = 'service_dependencies'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    source_service = db.Column(db.String(100), db.ForeignKey('services.service_key', ondelete='CASCADE'),
                               nullable=False)
    target_service = db.Column(db.String(100), db.ForeignKey('services.service_key', ondelete='CASCADE'),
                               nullable=False)
    relation_type = db.Column(db.String(50), default='calls')
    weight = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'source': self.source_service,
            'target': self.target_service,
            'label': self.relation_type
        }


class Metric(db.Model):
    __tablename__ = 'metrics'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    service_key = db.Column(db.String(100), db.ForeignKey('services.service_key', ondelete='CASCADE'), nullable=False)
    metric_name = db.Column(db.String(50), nullable=False)
    metric_value = db.Column(db.Numeric(10, 2), nullable=False)
    unit = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'value': float(self.metric_value)
        }


class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    service_key = db.Column(db.String(100), db.ForeignKey('services.service_key', ondelete='CASCADE'), nullable=False)
    metric_name = db.Column(db.String(50), nullable=False)
    metric_value = db.Column(db.Numeric(10, 2))
    anomaly_score = db.Column(db.Numeric(5, 4))
    severity = db.Column(db.Enum('info', 'warning', 'critical'), default='warning')
    status = db.Column(db.Enum('pending', 'confirmed', 'resolved'), default='pending')
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    llm_diagnosis = db.Column(db.Text)
    related_logs = db.Column(db.JSON)
    affected_services = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    confirmed_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))

    service = db.relationship('Service', backref='alerts')

    def to_dict(self):
        return {
            'id': self.id,
            'service_name': self.service_key,
            'metric_name': self.metric_name,
            'metric_value': float(self.metric_value) if self.metric_value else None,
            'anomaly_score': float(self.anomaly_score) if self.anomaly_score else None,
            'severity': self.severity,
            'status': self.status,
            'title': self.title,
            'description': self.description,
            'llm_diagnosis': self.llm_diagnosis,
            'related_logs': self.related_logs if self.related_logs else [],
            'affected_services': self.affected_services if self.affected_services else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


class AppLog(db.Model):
    __tablename__ = 'app_logs'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    service_key = db.Column(db.String(100), db.ForeignKey('services.service_key', ondelete='CASCADE'), nullable=False)
    log_level = db.Column(db.String(20), nullable=False)
    log_message = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(100))
    trace_id = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'level': self.log_level,
            'message': self.log_message,
            'source': self.source
        }


class NotificationSetting(db.Model):
    __tablename__ = 'notification_settings'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    email_enabled = db.Column(db.Integer, default=1)
    email = db.Column(db.String(100))
    sms_enabled = db.Column(db.Integer, default=0)
    phone = db.Column(db.String(20))
    webhook_enabled = db.Column(db.Integer, default=0)
    webhook_url = db.Column(db.String(500))
    alert_levels = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'email_enabled': bool(self.email_enabled),
            'email': self.email,
            'sms_enabled': bool(self.sms_enabled),
            'phone': self.phone,
            'webhook_enabled': bool(self.webhook_enabled),
            'webhook_url': self.webhook_url,
            'alert_levels': self.alert_levels if self.alert_levels else ['critical', 'warning']
        }


# ========== 导入异常检测和LLM分析模块 ==========
from anomaly_detector import AnomalyDetector
from llm_analyzer import llm_analyzer

# 创建异常检测器实例
detector = AnomalyDetector(contamination=0.05)


# ========== 用户相关接口 ==========

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    print(f"[INFO] 登录请求: {username}")

    if not username or not password:
        return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400

    password_hash = hashlib.md5(password.encode()).hexdigest()
    user = User.query.filter_by(username=username, password=password_hash, status=1).first()

    if not user:
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

    token = generate_token(username)

    return jsonify({
        'success': True,
        'message': '登录成功',
        'token': token,
        'user': user.to_dict()
    })


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    return jsonify({'success': True, 'message': '登出成功'})


@app.route('/api/auth/current', methods=['GET'])
def get_current_user_info():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401
    return jsonify({'success': True, 'user': user.to_dict()})


@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401

    user_dict = user.to_dict()
    if user_dict.get('avatar') and not user_dict['avatar'].startswith('http'):
        user_dict['avatar'] = f"http://localhost:5000{user_dict['avatar']}"

    return jsonify({'success': True, 'profile': user_dict})


@app.route('/api/user/profile', methods=['PUT'])
def update_user_profile():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    if 'name' in data:
        user.name = data['name']
    if 'email' in data:
        user.email = data['email']
    if 'phone' in data:
        user.phone = data['phone']
    if 'avatar' in data:
        avatar_data = data['avatar']
        if avatar_data and avatar_data.startswith('data:image'):
            import base64
            from werkzeug.utils import secure_filename

            img_data = avatar_data.split(',')[1]
            img_bytes = base64.b64decode(img_data)

            filename = f"avatar_{user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            filepath = os.path.join('static/avatars', filename)

            os.makedirs('static/avatars', exist_ok=True)
            with open(filepath, 'wb') as f:
                f.write(img_bytes)

            user.avatar = f'/static/avatars/{filename}'

    db.session.commit()

    user_dict = user.to_dict()
    if user_dict.get('avatar') and not user_dict['avatar'].startswith('http'):
        user_dict['avatar'] = f"http://localhost:5000{user_dict['avatar']}"

    return jsonify({'success': True, 'message': '资料更新成功', 'profile': user_dict})


@app.route('/api/user/password', methods=['PUT'])
def change_password():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    old_password = data.get('oldPassword')
    new_password = data.get('newPassword')

    old_hash = hashlib.md5(old_password.encode()).hexdigest()
    if user.password != old_hash:
        return jsonify({'success': False, 'message': '原密码错误'}), 400

    user.password = hashlib.md5(new_password.encode()).hexdigest()
    db.session.commit()

    return jsonify({'success': True, 'message': '密码修改成功'})


@app.route('/api/user/notification', methods=['GET'])
def get_notification_settings():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401

    settings = NotificationSetting.query.filter_by(user_id=user.id).first()
    if not settings:
        return jsonify({
            'success': True,
            'settings': {
                'email_enabled': True,
                'email': user.email,
                'sms_enabled': False,
                'phone': '',
                'webhook_enabled': False,
                'webhook_url': '',
                'alert_levels': ['critical', 'warning']
            }
        })

    return jsonify({'success': True, 'settings': settings.to_dict()})


@app.route('/api/user/notification', methods=['PUT'])
def update_notification_settings():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.get_json()
    settings = NotificationSetting.query.filter_by(user_id=user.id).first()

    if not settings:
        settings = NotificationSetting(user_id=user.id)
        db.session.add(settings)

    settings.email_enabled = 1 if data.get('email_enabled') else 0
    settings.email = data.get('email', user.email)
    settings.sms_enabled = 1 if data.get('sms_enabled') else 0
    settings.phone = data.get('phone', '')
    settings.webhook_enabled = 1 if data.get('webhook_enabled') else 0
    settings.webhook_url = data.get('webhook_url', '')
    settings.alert_levels = data.get('alert_levels', ['critical', 'warning'])

    db.session.commit()
    return jsonify({'success': True, 'message': '通知设置已更新', 'settings': settings.to_dict()})


# ========== 系统接口 ==========

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})


@app.route('/api/dashboard/overview', methods=['GET'])
def get_dashboard_overview():
    # 服务统计
    total_services = Service.query.count()
    healthy_services = Service.query.filter_by(status='healthy').count()
    warning_services = Service.query.filter_by(status='warning').count()
    critical_services = Service.query.filter_by(status='critical').count()

    # 告警统计
    pending_alerts = Alert.query.filter_by(status='pending').count()
    confirmed_alerts = Alert.query.filter_by(status='confirmed').count()

    # 服务健康列表
    services = Service.query.all()
    service_health = []
    for s in services:
        cpu_metric = Metric.query.filter_by(service_key=s.service_key, metric_name='cpu_usage') \
            .order_by(Metric.timestamp.desc()).first()
        memory_metric = Metric.query.filter_by(service_key=s.service_key, metric_name='memory_usage') \
            .order_by(Metric.timestamp.desc()).first()
        latency_metric = Metric.query.filter_by(service_key=s.service_key, metric_name='request_latency') \
            .order_by(Metric.timestamp.desc()).first()

        service_health.append({
            'name': s.service_name,
            'service_key': s.service_key,
            'status': s.status,
            'cpu': float(cpu_metric.metric_value) if cpu_metric else 0,
            'memory': float(memory_metric.metric_value) if memory_metric else 0,
            'latency': float(latency_metric.metric_value) if latency_metric else 0
        })

    # 最近告警
    recent_alerts = Alert.query.order_by(Alert.created_at.desc()).limit(5).all()

    # 告警趋势
    alert_trends = []
    for i in range(7):
        date = datetime.now() - timedelta(days=6 - i)
        start = date.replace(hour=0, minute=0, second=0)
        end = start + timedelta(days=1)
        critical = Alert.query.filter(Alert.severity == 'critical', Alert.created_at >= start,
                                      Alert.created_at < end).count()
        warning = Alert.query.filter(Alert.severity == 'warning', Alert.created_at >= start,
                                     Alert.created_at < end).count()
        info = Alert.query.filter(Alert.severity == 'info', Alert.created_at >= start, Alert.created_at < end).count()
        alert_trends.append({
            'date': date.strftime('%m-%d'),
            'critical': critical,
            'warning': warning,
            'info': info
        })

    return jsonify({
        'summary': {
            'total_services': total_services,
            'healthy_services': healthy_services,
            'warning_services': warning_services,
            'critical_services': critical_services,
            'pending_alerts': pending_alerts,
            'confirmed_alerts': confirmed_alerts
        },
        'alert_trends': alert_trends,
        'service_health': service_health,
        'recent_alerts': [a.to_dict() for a in recent_alerts]
    })


@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    status = request.args.get('status')
    severity = request.args.get('severity')
    service = request.args.get('service')
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)

    query = Alert.query
    if status:
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity)
    if service:
        query = query.filter(Alert.service_key == service)

    total = query.count()
    alerts = query.order_by(Alert.created_at.desc()).offset(offset).limit(limit).all()

    return jsonify({
        'alerts': [a.to_dict() for a in alerts],
        'total': total
    })


@app.route('/api/alerts/<int:alert_id>', methods=['GET'])
def get_alert_detail(alert_id):
    alert = Alert.query.get(alert_id)
    if not alert:
        return jsonify({'success': False, 'message': '告警不存在'}), 404

    result = alert.to_dict()

    # 获取相关日志
    logs = AppLog.query.filter(
        AppLog.service_key == alert.service_key,
        AppLog.timestamp >= alert.created_at - timedelta(minutes=30),
        AppLog.timestamp <= alert.created_at + timedelta(minutes=10)
    ).limit(20).all()
    result['related_logs'] = [log.to_dict() for log in logs]

    # 获取影响的服务
    affected = ServiceDependency.query.filter(
        (ServiceDependency.source_service == alert.service_key) |
        (ServiceDependency.target_service == alert.service_key)
    ).all()
    affected_services = set()
    for d in affected:
        affected_services.add(d.source_service)
        affected_services.add(d.target_service)
    result['affected_services'] = list(affected_services)

    # 获取指标历史
    metrics = Metric.query.filter(
        Metric.service_key == alert.service_key,
        Metric.metric_name == alert.metric_name,
        Metric.timestamp >= datetime.utcnow() - timedelta(hours=24)
    ).order_by(Metric.timestamp.asc()).all()
    result['metric_history'] = [m.to_dict() for m in metrics]

    return jsonify(result)


@app.route('/api/alerts/<int:alert_id>/status', methods=['PUT'])
def update_alert_status(alert_id):
    alert = Alert.query.get(alert_id)
    if not alert:
        return jsonify({'success': False, 'message': '告警不存在'}), 404

    data = request.get_json()
    new_status = data.get('status')
    user = get_current_user()

    alert.status = new_status
    if new_status == 'confirmed':
        alert.confirmed_at = datetime.utcnow()
        alert.confirmed_by = user.id if user else None
    elif new_status == 'resolved':
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = user.id if user else None

    db.session.commit()
    return jsonify({'success': True, 'message': f'状态已更新为 {new_status}'})


@app.route('/api/topology', methods=['GET'])
def get_topology():
    services = Service.query.all()
    nodes = [{'id': s.service_key, 'name': s.service_name, 'status': s.status} for s in services]

    dependencies = ServiceDependency.query.all()
    edges = [{'source': d.source_service, 'target': d.target_service, 'label': d.relation_type} for d in dependencies]

    return jsonify({'nodes': nodes, 'edges': edges})


@app.route('/api/detect/anomaly', methods=['POST'])
def detect_anomaly():
    """执行异常检测"""
    try:
        data = request.json or {}
        service_key = data.get('service_key')

        # 使用全局检测器
        global detector
        if detector is None:
            detector = init_detector(current_app._get_current_object())

        # 执行检测
        alerts = detector.detect_and_save(service_key=service_key)

        return jsonify({
            'success': True,
            'message': f'检测完成，发现 {len(alerts)} 个异常',
            'alerts_count': len(alerts),
            'alerts': [
                {
                    'id': alert.id,
                    'service_name': alert.service_name,
                    'metric_name': alert.metric_name,
                    'severity': alert.severity,
                    'description': alert.description
                }
                for alert in alerts
            ]
        })

    except Exception as e:
        import traceback
        print(f"Anomaly detection error: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/analyze/logs', methods=['POST'])
def analyze_logs():
    """分析日志并生成诊断 - 使用真实的 LLM 分析器"""
    print("[INFO] 执行日志智能分析...")
    data = request.get_json() or {}
    service_name = data.get('service_name')
    alert_id = data.get('alert_id')

    # 使用 LLM 分析器从数据库获取日志并分析
    diagnosis, logs = llm_analyzer.analyze_from_db(
        service_key=service_name,
        alert_id=alert_id,
        minutes=300
    )

    return jsonify({
        'success': True,
        'diagnosis': diagnosis,
        'logs': logs
    })


@app.route('/api/metrics/<service_key>', methods=['GET'])
def get_service_metrics(service_key):
    """获取服务指标历史"""
    metric_name = request.args.get('metric', 'cpu_usage')
    hours = request.args.get('hours', 24, type=int)

    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    metrics = Metric.query.filter(
        Metric.service_key == service_key,
        Metric.metric_name == metric_name,
        Metric.timestamp >= cutoff_time
    ).order_by(Metric.timestamp.asc()).all()

    return jsonify({
        'service_key': service_key,
        'metric_name': metric_name,
        'data': [m.to_dict() for m in metrics]
    })


if __name__ == '__main__':
    # 创建静态文件目录
    os.makedirs('static/avatars', exist_ok=True)
    app.run(debug=True, port=5000)