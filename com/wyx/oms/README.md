ops-platform/
├── backend/                 # Flask后端
│   ├── app.py              # 主应用
│   ├── requirements.txt    # 依赖
│   ├── config.py           # 配置
│   ├── models.py           # 数据模型
│   ├── anomaly_detector.py # 异常检测
│   ├── llm_analyzer.py     # LLM日志分析
│   └── mock_data.py        # Mock数据
├── frontend/               # Vue前端
│   ├── src/
│   │   ├── App.vue
│   │   ├── views/
│   │   │   ├── Dashboard.vue
│   │   │   ├── AlertList.vue
│   │   │   ├── AlertDetail.vue
│   │   │   └── Topology.vue
│   │   └── api/
│   │       └── index.js
│   ├── package.json
│   └── vite.config.js
└── docker-compose.yml      # 可选，快速启动依赖服务