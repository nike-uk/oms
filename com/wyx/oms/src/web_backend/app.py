from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import random
import hashlib
import jwt

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'  # 用于 session
app.config['SECRET_KEY'] = 'your-jwt-secret-key'
CORS(app, origins=['http://localhost:3000', 'http://127.0.0.1:3000'], supports_credentials=True)

# ========== 模拟用户数据 ==========
USERS = {
    'admin': {
        'id': 1,
        'username': 'admin',
        'password': hashlib.md5('admin123'.encode()).hexdigest(),  # admin123
        'name': '管理员',
        'email': 'admin@ops.com',
        'phone': '13800138000',
        'role': 'admin',
        'avatar': '',
        'created_at': '2025-01-01T00:00:00'
    },
    'user': {
        'id': 2,
        'username': 'user',
        'password': hashlib.md5('user123'.encode()).hexdigest(),  # user123
        'name': '普通用户',
        'email': 'user@ops.com',
        'phone': '13800138001',
        'role': 'user',
        'avatar': '',
        'created_at': '2025-01-02T00:00:00'
    }
}

# 当前登录用户（简化版，实际应该用 JWT）
current_user = None


def generate_token(username):
    """生成 JWT token"""
    payload = {
        'username': username,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')


def verify_token(token):
    """验证 JWT token"""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload['username']
    except:
        return None


# ========== 用户相关接口 ==========

@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    print(f"[INFO] 登录请求: {username}")

    if not username or not password:
        return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400

    user = USERS.get(username)
    if not user:
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

    password_hash = hashlib.md5(password.encode()).hexdigest()
    if user['password'] != password_hash:
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

    # 生成 token
    token = generate_token(username)

    # 返回用户信息（不包含密码）
    user_info = {k: v for k, v in user.items() if k != 'password'}

    return jsonify({
        'success': True,
        'message': '登录成功',
        'token': token,
        'user': user_info
    })


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """用户登出"""
    return jsonify({'success': True, 'message': '登出成功'})


@app.route('/api/auth/current', methods=['GET'])
def get_current_user():
    """获取当前登录用户信息"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'success': False, 'message': '未登录'}), 401

    token = auth_header.replace('Bearer ', '')
    username = verify_token(token)

    if not username:
        return jsonify({'success': False, 'message': '无效的token'}), 401

    user = USERS.get(username)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    user_info = {k: v for k, v in user.items() if k != 'password'}
    return jsonify({'success': True, 'user': user_info})


@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    """获取用户个人资料"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'success': False, 'message': '未登录'}), 401

    token = auth_header.replace('Bearer ', '')
    username = verify_token(token)

    if not username:
        return jsonify({'success': False, 'message': '无效的token'}), 401

    user = USERS.get(username)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    user_info = {k: v for k, v in user.items() if k != 'password'}
    return jsonify({'success': True, 'profile': user_info})


@app.route('/api/user/profile', methods=['PUT'])
def update_user_profile():
    """更新用户个人资料"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'success': False, 'message': '未登录'}), 401

    token = auth_header.replace('Bearer ', '')
    username = verify_token(token)

    if not username:
        return jsonify({'success': False, 'message': '无效的token'}), 401

    data = request.get_json()
    user = USERS.get(username)

    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    # 更新用户信息
    if 'name' in data:
        user['name'] = data['name']
    if 'email' in data:
        user['email'] = data['email']
    if 'phone' in data:
        user['phone'] = data['phone']
    if 'avatar' in data:
        user['avatar'] = data['avatar']

    return jsonify({
        'success': True,
        'message': '资料更新成功',
        'profile': {k: v for k, v in user.items() if k != 'password'}
    })


@app.route('/api/user/password', methods=['PUT'])
def change_password():
    """修改密码"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'success': False, 'message': '未登录'}), 401

    token = auth_header.replace('Bearer ', '')
    username = verify_token(token)

    if not username:
        return jsonify({'success': False, 'message': '无效的token'}), 401

    data = request.get_json()
    old_password = data.get('oldPassword')
    new_password = data.get('newPassword')

    user = USERS.get(username)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    # 验证旧密码
    old_hash = hashlib.md5(old_password.encode()).hexdigest()
    if user['password'] != old_hash:
        return jsonify({'success': False, 'message': '原密码错误'}), 400

    # 更新密码
    user['password'] = hashlib.md5(new_password.encode()).hexdigest()

    return jsonify({'success': True, 'message': '密码修改成功'})


@app.route('/api/user/notification', methods=['GET'])
def get_notification_settings():
    """获取通知设置"""
    return jsonify({
        'success': True,
        'settings': {
            'email_enabled': True,
            'email': 'admin@ops.com',
            'sms_enabled': False,
            'phone': '',
            'webhook_enabled': False,
            'webhook_url': '',
            'alert_levels': ['critical', 'warning']
        }
    })


@app.route('/api/user/notification', methods=['PUT'])
def update_notification_settings():
    """更新通知设置"""
    data = request.get_json()
    return jsonify({'success': True, 'message': '通知设置已更新', 'settings': data})

# 临时跳过数据库，直接用 Mock 数据
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})


@app.route('/api/dashboard/overview', methods=['GET'])
def get_dashboard_overview():
    """获取仪表盘概览数据 - Mock版"""
    services = ['api-gateway', 'user-service', 'order-service', 'payment-service', 'inventory-service']

    return jsonify({
        'summary': {
            'total_services': 5,
            'healthy_services': 3,
            'warning_services': 1,
            'critical_services': 1,
            'pending_alerts': 4,
            'confirmed_alerts': 2
        },
        'alert_trends': generate_alert_trends(),
        'service_health': generate_service_health(services),
        'recent_alerts': generate_recent_alerts(5, services)
    })


def generate_alert_trends():
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


def generate_service_health(services):
    """生成服务健康状态"""
    health_data = []
    for service in services:
        health_data.append({
            'name': service,
            'status': random.choice(['healthy', 'warning', 'critical']),
            'cpu': round(random.uniform(10, 90), 1),
            'memory': round(random.uniform(20, 85), 1),
            'latency': round(random.uniform(10, 500), 0)
        })
    return health_data


def generate_recent_alerts(count, services):
    """生成最近的告警"""
    metrics = ['cpu_usage', 'memory_usage', 'request_latency', 'error_rate']
    alerts = []
    for i in range(count):
        service = random.choice(services)
        metric = random.choice(metrics)
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


@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """获取告警列表"""
    services = ['api-gateway', 'user-service', 'order-service', 'payment-service', 'inventory-service']
    limit = request.args.get('limit', 50, type=int)

    alerts = generate_recent_alerts(limit, services)

    return jsonify({
        'alerts': alerts,
        'total': len(alerts)
    })


@app.route('/api/alerts/<int:alert_id>', methods=['GET'])
def get_alert_detail(alert_id):
    """获取告警详情"""
    services = ['api-gateway', 'user-service', 'order-service', 'payment-service', 'inventory-service']
    service = random.choice(services)

    return jsonify({
        'id': alert_id,
        'service_name': service,
        'metric_name': 'request_latency',
        'metric_value': 850.5,
        'anomaly_score': 0.85,
        'severity': 'critical',
        'status': 'pending',
        'description': f'{service} 响应延迟异常，当前值850ms',
        'llm_diagnosis': '检测到大量数据库连接超时异常。可能原因：1) 数据库连接池配置过小 2) 数据库服务负载过高。建议：检查连接池配置，查看数据库慢查询日志。',
        'related_logs': [
            {'timestamp': datetime.now().isoformat(), 'level': 'ERROR',
             'message': 'database connection pool exhausted'},
            {'timestamp': datetime.now().isoformat(), 'level': 'WARN',
             'message': 'slow query detected: SELECT * FROM orders (took 5.2s)'}
        ],
        'affected_services': ['api-gateway', 'payment-service', 'inventory-service'],
        'created_at': datetime.utcnow().isoformat(),
        'metric_history': generate_metric_history(service, 'request_latency')
    })


def generate_metric_history(service_name, metric_name, hours=24):
    """生成指标历史数据"""
    data = []
    now = datetime.now()

    for i in range(hours * 12):  # 每5分钟一个点
        timestamp = now - timedelta(minutes=hours * 60 - i * 5)
        base_value = 100 + random.uniform(-30, 50)
        if random.random() < 0.05:
            base_value = 850 + random.uniform(0, 200)

        data.append({
            'timestamp': timestamp.isoformat(),
            'value': round(max(0, base_value), 2)
        })

    return data


@app.route('/api/topology', methods=['GET'])
def get_topology():
    """获取服务拓扑数据"""
    nodes = [
        {'id': 'api-gateway', 'name': 'API Gateway', 'status': 'warning'},
        {'id': 'user-service', 'name': 'User Service', 'status': 'healthy'},
        {'id': 'order-service', 'name': 'Order Service', 'status': 'critical'},
        {'id': 'payment-service', 'name': 'Payment Service', 'status': 'healthy'},
        {'id': 'inventory-service', 'name': 'Inventory Service', 'status': 'healthy'}
    ]

    edges = [
        {'source': 'api-gateway', 'target': 'user-service', 'label': 'calls'},
        {'source': 'api-gateway', 'target': 'order-service', 'label': 'calls'},
        {'source': 'api-gateway', 'target': 'payment-service', 'label': 'calls'},
        {'source': 'order-service', 'target': 'user-service', 'label': 'calls'},
        {'source': 'order-service', 'target': 'inventory-service', 'label': 'calls'},
        {'source': 'payment-service', 'target': 'user-service', 'label': 'calls'}
    ]

    return jsonify({'nodes': nodes, 'edges': edges})


@app.route('/api/detect/anomaly', methods=['POST'])
def detect_anomaly():
    """执行异常检测"""
    try:
        data = request.get_json() or {}
        service_name = data.get('service_name')

        # 定义检测指标
        metrics_config = [
            {'name': 'cpu_usage', 'threshold': 2.0},
            {'name': 'memory_usage', 'threshold': 1.8},
            {'name': 'request_latency', 'threshold': 3.0},
            {'name': 'error_rate', 'threshold': 2.5}
        ]

        services = ['api-gateway', 'user-service', 'order-service', 'payment-service', 'inventory-service']
        if service_name:
            services = [service_name]

        all_alerts = []
        for service in services:
            for metric_config in metrics_config:
                # 模拟检测，随机生成一些异常
                if random.random() < 0.3:  # 30% 概率生成异常
                    severity = random.choice(['warning', 'critical'])
                    value = random.uniform(80, 95) if metric_config['name'] in ['cpu_usage',
                                                                                'memory_usage'] else random.uniform(500,
                                                                                                                    1000)

                    all_alerts.append({
                        'service_name': service,
                        'metric_name': metric_config['name'],
                        'metric_value': round(value, 2),
                        'anomaly_score': round(random.uniform(0.6, 0.95), 2),
                        'severity': severity,
                        'description': f'{service} {metric_config["name"]} 异常'
                    })

        return jsonify({
            'success': True,
            'alerts_generated': len(all_alerts),
            'alerts': all_alerts
        })
    except Exception as e:
        print(f"Anomaly detection error: {e}")
        return jsonify({
            'success': False,
            'alerts_generated': 0,
            'alerts': [],
            'error': str(e)
        }), 500

@app.route('/api/alerts/<int:alert_id>/status', methods=['PUT'])
def update_alert_status(alert_id):
    """更新告警状态"""
    data = request.get_json()
    new_status = data.get('status')
    print(f"[INFO] 更新告警 {alert_id} 状态为: {new_status}")
    return jsonify({
        'success': True,
        'message': f'Alert {alert_id} status updated to {new_status}'
    })


@app.route('/api/analyze/logs', methods=['POST'])
def analyze_logs():
    """分析日志并生成诊断"""
    print("[INFO] 执行日志智能分析...")
    data = request.get_json() or {}
    service_name = data.get('service_name', 'unknown')

    # 模拟诊断结果
    diagnoses = [
        f'[{service_name}] 检测到大量数据库连接超时异常。可能原因：1) 数据库连接池配置过小 2) 数据库服务负载过高 3) 网络延迟。建议：检查连接池配置，查看数据库慢查询日志。',
        f'[{service_name}] 发现内存使用持续增长，疑似内存泄漏。可能原因：1) 未正确释放对象引用 2) 缓存未设置过期时间。建议：使用内存分析工具检查堆内存。',
        f'[{service_name}] 服务响应时间增加，伴随CPU使用率上升。可能原因：1) 业务流量突增 2) 存在慢接口或死循环。建议：检查QPS变化，分析接口耗时分布。',
        f'[{service_name}] 日志中出现大量认证失败记录。可能原因：1) 凭证过期 2) 第三方认证服务异常。建议：检查认证配置和外部服务状态。'
    ]

    return jsonify({
        'success': True,
        'diagnosis': random.choice(diagnoses),
        'logs': [
            {'timestamp': datetime.now().isoformat(), 'level': 'ERROR', 'message': 'Connection timeout after 30s'},
            {'timestamp': datetime.now().isoformat(), 'level': 'WARN', 'message': 'Retry attempt 1/3'},
            {'timestamp': datetime.now().isoformat(), 'level': 'ERROR', 'message': 'Failed to connect to database'}
        ]
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)