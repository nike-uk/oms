"""
孤立森林(Isolation Forest)完整实现
功能包括：算法实现、可视化、示例应用
"""

import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import make_blobs, make_moons, make_circles
from sklearn.preprocessing import StandardScaler
import seaborn as sns
from scipy.spatial import ConvexHull
import warnings

warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


# ==================== 第一部分：孤立森林算法实现 ====================

class IsolationTree:
    """单棵孤立树"""

    def __init__(self, max_height=10):
        self.max_height = max_height
        self.tree = None

    def _build_tree(self, X, current_height):
        """
        递归构建孤立树
        """
        n_samples, n_features = X.shape

        # 停止条件
        if current_height >= self.max_height or n_samples <= 1:
            return {
                'type': 'leaf',
                'size': n_samples,
                'height': current_height
            }

        # 随机选择特征和分割点
        feature_idx = np.random.randint(0, n_features)
        feature_min = np.min(X[:, feature_idx])
        feature_max = np.max(X[:, feature_idx])

        # 如果所有特征值相同，停止划分
        if feature_min == feature_max:
            return {
                'type': 'leaf',
                'size': n_samples,
                'height': current_height
            }

        # 随机选择分割点
        split_value = np.random.uniform(feature_min, feature_max)

        # 划分左右子树
        left_mask = X[:, feature_idx] < split_value
        right_mask = ~left_mask

        # 递归构建子树
        return {
            'type': 'internal',
            'feature': feature_idx,
            'split_value': split_value,
            'height': current_height,
            'left': self._build_tree(X[left_mask], current_height + 1),
            'right': self._build_tree(X[right_mask], current_height + 1)
        }

    def fit(self, X):
        """训练孤立树"""
        self.tree = self._build_tree(X, 0)
        return self

    def _path_length(self, x, node):
        """计算单个样本在树中的路径长度"""
        if node['type'] == 'leaf':
            # 对于叶子节点，返回修正的路径长度
            n = node['size']
            if n <= 1:
                return node['height']
            else:
                # c(n) - 二叉搜索树中不成功搜索的平均路径长度
                c_n = 2 * (np.log(n - 1) + 0.5772156649) - 2 * (n - 1) / n
                return node['height'] + c_n
        else:
            # 内部节点，根据特征值选择子树
            if x[node['feature']] < node['split_value']:
                return self._path_length(x, node['left'])
            else:
                return self._path_length(x, node['right'])

    def path_length(self, X):
        """计算多个样本的路径长度"""
        if self.tree is None:
            raise ValueError("树未训练，请先调用fit方法")

        if X.ndim == 1:
            X = X.reshape(1, -1)

        n_samples = X.shape[0]
        paths = np.zeros(n_samples)

        for i in range(n_samples):
            paths[i] = self._path_length(X[i], self.tree)

        return paths


class IsolationForest:
    """完整的孤立森林实现"""

    def __init__(self, n_estimators=100, max_samples=256, contamination=0.1, random_state=None):
        """
        参数:
        ----------
        n_estimators : int, 默认=100
            孤立树的数量
        max_samples : int or float, 默认=256
            每棵树使用的最大样本数
        contamination : float, 默认=0.1
            数据集中异常点的预期比例
        random_state : int, 默认=None
            随机种子
        """
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.contamination = contamination
        self.random_state = random_state
        self.trees = []
        self.sample_size_ = None

        if random_state is not None:
            np.random.seed(random_state)

    def fit(self, X):
        """
        训练孤立森林

        参数:
        ----------
        X : array-like, shape (n_samples, n_features)
            训练数据
        """
        X = np.asarray(X)
        n_samples, n_features = X.shape

        # 确定每棵树的样本大小
        if isinstance(self.max_samples, float):
            if 0 < self.max_samples <= 1:
                self.sample_size_ = max(1, int(self.max_samples * n_samples))
            else:
                raise ValueError("max_samples为浮点数时应在(0, 1]范围内")
        else:
            self.sample_size_ = min(self.max_samples, n_samples)

        # 计算最大树高（类似二叉搜索树的高度）
        max_height = int(np.ceil(np.log2(self.sample_size_)))

        # 构建多棵孤立树
        print(f"构建孤立森林: {self.n_estimators}棵树, 每棵树{self.sample_size_}个样本, 最大高度{max_height}")

        for i in range(self.n_estimators):
            # 随机采样（不放回）
            if self.sample_size_ < n_samples:
                sample_idx = np.random.choice(n_samples, self.sample_size_, replace=False)
                X_sample = X[sample_idx]
            else:
                X_sample = X

            # 构建并训练一棵树
            tree = IsolationTree(max_height=max_height)
            tree.fit(X_sample)
            self.trees.append(tree)

            if (i + 1) % (self.n_estimators // 10) == 0:
                print(f"  已构建 {i + 1}/{self.n_estimators} 棵树")

        print("孤立森林构建完成!")
        return self

    def decision_function(self, X):
        """
        计算样本的异常分数（决策函数）
        返回的值越小表示越异常
        """
        X = np.asarray(X)
        n_samples = X.shape[0]

        if len(self.trees) == 0:
            raise ValueError("模型未训练，请先调用fit方法")

        # 计算每个样本在所有树中的平均路径长度
        avg_path_lengths = np.zeros(n_samples)

        for tree in self.trees:
            avg_path_lengths += tree.path_length(X)

        avg_path_lengths /= len(self.trees)

        # 计算标准化常数c(n)
        n = self.sample_size_
        if n > 1:
            c_n = 2 * (np.log(n - 1) + 0.5772156649) - 2 * (n - 1) / n
        else:
            c_n = 1

        # 计算异常分数
        anomaly_scores = 2 ** (-avg_path_lengths / c_n)

        # 转换为决策函数值（负值表示异常）
        decision_scores = -anomaly_scores

        return decision_scores

    def anomaly_score(self, X):
        """
        计算异常分数
        返回的值越大表示越异常（范围0-1）
        """
        decision_scores = self.decision_function(X)
        anomaly_scores = -decision_scores
        return anomaly_scores

    def predict(self, X, threshold=None):
        """
        预测样本是否为异常

        参数:
        ----------
        X : array-like, shape (n_samples, n_features)
            输入数据
        threshold : float, 默认=None
            异常阈值，如果为None则使用contamination参数

        返回:
        ----------
        labels : array, shape (n_samples,)
            1表示异常，0表示正常
        """
        anomaly_scores = self.anomaly_score(X)

        if threshold is None:
            # 根据contamination确定阈值
            threshold = np.percentile(anomaly_scores, 100 * (1 - self.contamination))

        return (anomaly_scores > threshold).astype(int)


# ==================== 第二部分：可视化工具 ====================

def plot_isolation_process(X, model, sample_indices=None, n_splits=3):
    """
    可视化孤立过程

    参数:
    ----------
    X : array-like, 原始数据
    model : IsolationForest, 训练好的模型
    sample_indices : list, 要可视化的样本索引
    n_splits : int, 要显示的分割次数
    """
    if sample_indices is None:
        sample_indices = [0, len(X) // 2, len(X) - 1]

    fig, axes = plt.subplots(1, len(sample_indices), figsize=(5 * len(sample_indices), 5))
    if len(sample_indices) == 1:
        axes = [axes]

    colors = plt.cm.tab10(np.arange(len(sample_indices)))

    for idx, (sample_idx, ax) in enumerate(zip(sample_indices, axes)):
        sample = X[sample_idx]

        # 选择一棵树进行可视化
        tree = model.trees[0]

        # 模拟孤立过程
        ax.scatter(X[:, 0], X[:, 1], c='lightblue', alpha=0.5, s=30, label='其他点')
        ax.scatter(sample[0], sample[1], c=colors[idx], s=100, marker='*',
                   label=f'样本 {sample_idx}', edgecolors='black', linewidth=1.5)

        node = tree.tree
        depth = 0

        while depth < n_splits and node['type'] == 'internal':
            feature = node['feature']
            split_value = node['split_value']

            if feature == 0:
                # 垂直分割
                ax.axvline(x=split_value, color='red', linestyle='--', alpha=0.7,
                           linewidth=1.5, label=f'分割{depth + 1}' if depth == 0 else None)
            else:
                # 水平分割
                ax.axhline(y=split_value, color='green', linestyle='--', alpha=0.7,
                           linewidth=1.5, label=f'分割{depth + 1}' if depth == 0 else None)

            # 决定下一步走哪个子树
            if sample[feature] < split_value:
                node = node['left']
            else:
                node = node['right']

            depth += 1

        ax.set_xlabel('特征 1')
        ax.set_ylabel('特征 2')
        ax.set_title(f'样本 {sample_idx} 的孤立过程')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


def plot_anomaly_detection_results(X, y_true, y_pred, anomaly_scores, dataset_name=""):
    """
    可视化异常检测结果

    参数:
    ----------
    X : array-like, 特征数据
    y_true : array-like, 真实标签
    y_pred : array-like, 预测标签
    anomaly_scores : array-like, 异常分数
    dataset_name : str, 数据集名称
    """
    fig = plt.figure(figsize=(15, 10))

    # 1. 真实标签可视化
    ax1 = plt.subplot(2, 3, 1)
    normal_idx = y_true == 0
    anomaly_idx = y_true == 1

    ax1.scatter(X[normal_idx, 0], X[normal_idx, 1],
                c='blue', alpha=0.6, s=30, label='正常点')
    ax1.scatter(X[anomaly_idx, 0], X[anomaly_idx, 1],
                c='red', alpha=0.8, s=50, marker='x', label='真实异常点')

    # 添加凸包（正常点区域）
    if sum(normal_idx) > 2:
        try:
            hull = ConvexHull(X[normal_idx])
            for simplex in hull.simplices:
                ax1.plot(X[normal_idx][simplex, 0], X[normal_idx][simplex, 1],
                         'b-', alpha=0.2, linewidth=2)
        except:
            pass

    ax1.set_xlabel('特征 1')
    ax1.set_ylabel('特征 2')
    ax1.set_title(f'{dataset_name} - 真实标签')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. 异常分数可视化
    ax2 = plt.subplot(2, 3, 2)
    scatter = ax2.scatter(X[:, 0], X[:, 1], c=anomaly_scores,
                          cmap='viridis', alpha=0.7, s=50)
    plt.colorbar(scatter, ax=ax2, label='异常分数')
    ax2.set_xlabel('特征 1')
    ax2.set_ylabel('特征 2')
    ax2.set_title(f'{dataset_name} - 异常分数热图')
    ax2.grid(True, alpha=0.3)

    # 3. 预测结果可视化
    ax3 = plt.subplot(2, 3, 3)
    normal_pred_idx = y_pred == 0
    anomaly_pred_idx = y_pred == 1

    ax3.scatter(X[normal_pred_idx, 0], X[normal_pred_idx, 1],
                c='lightblue', alpha=0.6, s=30, label='预测正常点')
    ax3.scatter(X[anomaly_pred_idx, 0], X[anomaly_pred_idx, 1],
                c='orange', alpha=0.8, s=80, marker='s', label='预测异常点')

    ax3.set_xlabel('特征 1')
    ax3.set_ylabel('特征 2')
    ax3.set_title(f'{dataset_name} - 预测结果')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 4. 异常分数分布
    ax4 = plt.subplot(2, 3, 4)
    ax4.hist(anomaly_scores[y_true == 0], bins=20, alpha=0.7,
             color='blue', label='正常点', density=True)
    ax4.hist(anomaly_scores[y_true == 1], bins=10, alpha=0.7,
             color='red', label='异常点', density=True)
    ax4.axvline(x=np.percentile(anomaly_scores, 90), color='black',
                linestyle='--', label='90%分位数')
    ax4.set_xlabel('异常分数')
    ax4.set_ylabel('密度')
    ax4.set_title('异常分数分布')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 5. 混淆矩阵
    ax5 = plt.subplot(2, 3, 5)
    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(y_true, y_pred)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax5,
                xticklabels=['预测正常', '预测异常'],
                yticklabels=['真实正常', '真实异常'])
    ax5.set_title('混淆矩阵')

    # 6. 性能指标
    ax6 = plt.subplot(2, 3, 6)
    ax6.axis('off')

    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    metrics_text = (
        f'准确率: {accuracy:.3f}\n'
        f'精确率: {precision:.3f}\n'
        f'召回率: {recall:.3f}\n'
        f'F1分数: {f1:.3f}\n'
        f'异常比例: {np.mean(y_pred):.3f}\n'
        f'异常分数均值: {np.mean(anomaly_scores):.3f}'
    )

    ax6.text(0.1, 0.5, metrics_text, fontsize=12, verticalalignment='center',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    ax6.set_title('性能指标')

    plt.tight_layout()
    plt.show()


# ==================== 第三部分：示例数据集 ====================

def generate_datasets():
    """生成多种类型的示例数据集"""
    datasets = {}

    # 1. 高斯分布数据集（简单）
    np.random.seed(42)
    X1 = np.random.randn(300, 2)
    X1 = np.vstack([X1, np.random.randn(20, 2) * 3 + 5])  # 添加异常点
    y1 = np.array([0] * 300 + [1] * 20)
    datasets['高斯分布'] = (X1, y1)

    # 2. 月牙形数据集（非线性）
    X2, y2 = make_moons(n_samples=300, noise=0.1, random_state=42)
    # 添加异常点
    anomalies2 = np.array([[1.5, -0.5], [1.0, 1.2], [-1.5, 0.5], [-0.5, -1.0]])
    X2 = np.vstack([X2, anomalies2])
    y2 = np.array([0] * 300 + [1] * 4)
    datasets['月牙形'] = (X2, y2)

    # 3. 圆形数据集（环状）
    X3, y3 = make_circles(n_samples=300, noise=0.05, factor=0.5, random_state=42)
    # 添加异常点
    anomalies3 = np.array([[0, 0], [1.5, 1.5], [-1.5, -1.5], [2, 0], [0, 2]])
    X3 = np.vstack([X3, anomalies3])
    y3 = np.array([0] * 300 + [1] * 5)
    datasets['圆形'] = (X3, y3)

    # 4. 多簇数据集
    X4, y4 = make_blobs(n_samples=300, centers=3, n_features=2,
                        cluster_std=0.8, random_state=42)
    # 添加异常点
    anomalies4 = np.array([[10, 10], [-10, -10], [10, -10], [-10, 10], [15, 0]])
    X4 = np.vstack([X4, anomalies4])
    y4 = np.array([0] * 300 + [1] * 5)
    datasets['多簇'] = (X4, y4)

    return datasets


# ==================== 第四部分：主程序 ====================

def main():
    """主程序：演示孤立森林的完整功能"""
    print("=" * 60)
    print("孤立森林(Isolation Forest)完整实现演示")
    print("=" * 60)

    # 1. 生成数据集
    print("\n1. 生成示例数据集...")
    datasets = generate_datasets()

    # 2. 对每个数据集应用孤立森林
    for dataset_name, (X, y_true) in datasets.items():
        print(f"\n{'=' * 40}")
        print(f"数据集: {dataset_name}")
        print(f"样本数: {X.shape[0]}, 特征数: {X.shape[1]}")
        print(f"异常比例: {np.mean(y_true):.3f}")
        print(f"{'=' * 40}")

        # 标准化数据
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # 3. 创建和训练孤立森林
        print("训练孤立森林...")
        iso_forest = IsolationForest(
            n_estimators=100,
            max_samples=0.8,  # 使用80%的样本
            contamination=0.1,  # 预期异常比例为10%
            random_state=42
        )

        iso_forest.fit(X_scaled)

        # 4. 预测
        print("进行预测...")
        y_pred = iso_forest.predict(X_scaled)
        anomaly_scores = iso_forest.anomaly_score(X_scaled)

        # 5. 可视化结果
        print("生成可视化结果...")
        plot_anomaly_detection_results(
            X_scaled, y_true, y_pred, anomaly_scores, dataset_name
        )

        # 6. 可视化孤立过程（对第一个数据集）
        if dataset_name == "高斯分布":
            print("\n可视化孤立过程...")
            plot_isolation_process(X_scaled, iso_forest,
                                   sample_indices=[0, 150, 310], n_splits=3)

        # 7. 显示详细信息
        print("\n异常分数统计:")
        print(f"  最小值: {anomaly_scores.min():.4f}")
        print(f"  最大值: {anomaly_scores.max():.4f}")
        print(f"  中位数: {np.median(anomaly_scores):.4f}")
        print(f"  平均值: {anomaly_scores.mean():.4f}")

        # 计算性能指标
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)

        print("\n性能指标:")
        print(f"  准确率: {accuracy:.4f}")
        print(f"  精确率: {precision:.4f}")
        print(f"  召回率: {recall:.4f}")
        print(f"  F1分数: {f1:.4f}")

    # 8. 高级应用示例：模拟网络入侵检测
    print("\n" + "=" * 60)
    print("高级应用示例：模拟网络入侵检测")
    print("=" * 60)

    # 模拟网络流量数据
    np.random.seed(42)
    n_normal = 1000
    n_attack = 50

    # 正常流量特征
    normal_features = {
        'duration': np.random.exponential(10, n_normal),  # 连接时长
        'packet_count': np.random.poisson(100, n_normal),  # 数据包数量
        'byte_count': np.random.exponential(1000, n_normal),  # 字节数
        'ports': np.random.randint(1, 100, n_normal)  # 目标端口
    }

    # 攻击流量特征
    attack_features = {
        'duration': np.random.exponential(100, n_attack),  # 更长连接
        'packet_count': np.random.poisson(1000, n_attack),  # 更多数据包
        'byte_count': np.random.exponential(10000, n_attack),  # 更多字节
        'ports': np.random.randint(200, 300, n_attack)  # 非常用端口
    }

    # 创建特征矩阵
    X_network = np.column_stack([
        np.concatenate([normal_features['duration'], attack_features['duration']]),
        np.concatenate([normal_features['packet_count'], attack_features['packet_count']]),
        np.concatenate([normal_features['byte_count'], attack_features['byte_count']]),
        np.concatenate([normal_features['ports'], attack_features['ports']])
    ])

    y_network = np.array([0] * n_normal + [1] * n_attack)

    print(f"网络流量数据: {X_network.shape}")
    print(f"正常流量: {n_normal}, 攻击流量: {n_attack}")

    # 标准化
    scaler = StandardScaler()
    X_network_scaled = scaler.fit_transform(X_network)

    # 训练孤立森林
    print("\n训练网络入侵检测模型...")
    network_forest = IsolationForest(
        n_estimators=150,
        max_samples=0.7,
        contamination=0.05,  # 预期攻击比例为5%
        random_state=42
    )

    network_forest.fit(X_network_scaled)

    # 预测
    network_pred = network_forest.predict(X_network_scaled)
    network_scores = network_forest.anomaly_score(X_network_scaled)

    # 评估
    from sklearn.metrics import classification_report
    print("\n网络入侵检测结果:")
    print(classification_report(y_network, network_pred,
                                target_names=['正常流量', '攻击流量']))

    # 可视化部分特征
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    feature_names = ['连接时长', '数据包数量', '字节数', '目标端口']

    for i, ax in enumerate(axes.flat):
        if i < 4:
            normal_vals = X_network[y_network == 0, i]
            attack_vals = X_network[y_network == 1, i]

            ax.hist(normal_vals, bins=30, alpha=0.7, color='blue',
                    label='正常流量', density=True)
            ax.hist(attack_vals, bins=15, alpha=0.7, color='red',
                    label='攻击流量', density=True)

            ax.set_xlabel(feature_names[i])
            ax.set_ylabel('密度')
            ax.set_title(f'{feature_names[i]}分布')
            ax.legend()
            ax.grid(True, alpha=0.3)

    plt.suptitle('网络流量特征分布', fontsize=16)
    plt.tight_layout()
    plt.show()

    # 9. 总结
    print("\n" + "=" * 60)
    print("孤立森林算法总结")
    print("=" * 60)
    print("""
    算法特点:
    1. 无监督学习: 不需要标签数据
    2. 高效: 时间复杂度接近线性
    3. 适用于高维数据: 不需要计算距离或密度
    4. 对异常敏感: 异常点容易被快速孤立

    关键参数:
    1. n_estimators: 树的数量，越多越稳定但计算成本越高
    2. max_samples: 每棵树的样本数，控制树的大小
    3. contamination: 预期异常比例，影响阈值选择
    4. max_features: 每次分割考虑的特征数

    应用场景:
    1. 欺诈检测
    2. 网络入侵检测
    3. 工业异常检测
    4. 医疗异常诊断
    5. 数据清洗

    注意事项:
    1. 对于高维稀疏数据效果可能不佳
    2. 可能需要调整参数以适应不同数据分布
    3. 对于局部密集的异常点可能不敏感
    """)

    print("\n程序执行完成！")


# ==================== 第五部分：使用说明 ====================

def usage_example():
    """快速使用示例"""
    print("快速使用示例:")
    print("-" * 40)

    # 1. 创建数据
    np.random.seed(42)
    X = np.random.randn(200, 2)
    X = np.vstack([X, np.array([[5, 5], [-5, -5], [5, -5], [-5, 5]])])

    # 2. 创建模型
    iso_forest = IsolationForest(
        n_estimators=50,
        max_samples=0.8,
        contamination=0.05,
        random_state=42
    )

    # 3. 训练模型
    iso_forest.fit(X)

    # 4. 预测
    predictions = iso_forest.predict(X)
    scores = iso_forest.anomaly_score(X)

    # 5. 显示结果
    print(f"数据集大小: {X.shape}")
    print(f"检测到的异常点: {sum(predictions)}")
    print(f"异常分数范围: [{scores.min():.3f}, {scores.max():.3f}]")

    # 6. 可视化
    plt.figure(figsize=(10, 4))

    plt.subplot(1, 2, 1)
    plt.scatter(X[:, 0], X[:, 1], c='blue', alpha=0.6, s=30)
    plt.title('原始数据')
    plt.xlabel('特征1')
    plt.ylabel('特征2')
    plt.grid(True, alpha=0.3)

    plt.subplot(1, 2, 2)
    plt.scatter(X[:, 0], X[:, 1], c=scores, cmap='viridis', alpha=0.8, s=50)
    plt.colorbar(label='异常分数')
    plt.title('异常检测结果')
    plt.xlabel('特征1')
    plt.ylabel('特征2')
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


# ==================== 运行程序 ====================

if __name__ == "__main__":
    # 运行完整演示
    main()

    # 或者运行快速示例
    # usage_example()