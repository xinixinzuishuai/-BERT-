# ==============================================================================
# 文件: config.py
# ==============================================================================
# 本文件是整个项目的【配置中心】，所有模块的参数都从这里读取。
# 采用"集中式配置"设计模式，避免硬编码散落在各处，方便统一管理。
#
# 【功能索引】（Ctrl+F 搜索关键词可快速定位）
#   [配置-路径]   BASE_DIR, MODEL_DIR, DATA_DIR, LOGS_DIR
#   [配置-BERT]   BERT_MODEL_NAME, MAX_LENGTH, BATCH_SIZE
#   [配置-Flask]  FLASK_HOST, FLASK_PORT, FLASK_DEBUG
#   [配置-数据库]  SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
# ==============================================================================

import os

class Config:
    # --------------------------------------------------------------------------
    # [配置-路径] 项目目录结构
    # --------------------------------------------------------------------------
    # BASE_DIR: 项目根目录，所有相对路径的起点
    #   答辩要点：使用 os.path.dirname(os.path.abspath(__file__)) 动态获取
    #   当前文件所在目录，而不是硬编码绝对路径，这样项目迁移到其他机器
    #   时无需修改任何配置，符合软件工程"可移植性"原则。
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # MODEL_DIR: BERT 模型文件存放目录（如 pytorch_model.bin、config.json）
    MODEL_DIR = os.path.join(BASE_DIR, 'models')

    # DATA_DIR: SQLite 数据库文件存放目录
    DATA_DIR = os.path.join(BASE_DIR, 'data')

    # LOGS_DIR: 日志文件存放目录
    LOGS_DIR = os.path.join(BASE_DIR, 'logs')

    # --------------------------------------------------------------------------
    # [配置-BERT] 情感分析模型参数
    # --------------------------------------------------------------------------
    # BERT_MODEL_NAME: 模型路径或 HuggingFace 模型名称
    #   答辩要点：这里指向本地 models/bert-base-chinese 目录，
    #   采用"离线加载"策略，避免每次启动都从网络下载模型，
    #   保证在无网络环境下也能正常运行。
    BERT_MODEL_NAME = os.path.join(MODEL_DIR, 'bert-base-chinese')

    # MAX_LENGTH: 分词时单条文本的最大长度（token 数）
    #   答辩要点：BERT 模型的输入上限是 512 个 token，但微博评论通常
    #   较短，设为 128 既够用又能大幅减少显存/内存占用，加快推理速度。
    MAX_LENGTH = 128

    # BATCH_SIZE: 批量推理时每批处理的样本数
    #   答辩要点：批量处理比逐条推理效率高得多（GPU/CPU 并行计算），
    #   32 是在 CPU 环境下兼顾速度和内存的经验值。
    BATCH_SIZE = 32

    # --------------------------------------------------------------------------
    # [配置-Flask] Web 服务器参数
    # --------------------------------------------------------------------------
    # FLASK_HOST: 监听地址
    #   '0.0.0.0' 表示监听所有网卡，允许局域网内其他设备访问
    #   如果只允许本机访问，可改为 '127.0.0.1'
    FLASK_HOST = '0.0.0.0'

    # FLASK_PORT: 监听端口
    FLASK_PORT = 8000

    # FLASK_DEBUG: 是否开启调试模式
    #   生产环境务必设为 False，否则有安全风险（暴露堆栈信息、允许任意执行代码）
    FLASK_DEBUG = False

    # --------------------------------------------------------------------------
    # [配置-数据库] SQLAlchemy 连接参数
    # --------------------------------------------------------------------------
    # SQLALCHEMY_DATABASE_URI: 数据库连接字符串
    #   格式: sqlite:///绝对路径/weibo.db
    #   答辩要点：选用 SQLite 而非 MySQL/PostgreSQL 的原因：
    #   1. 零配置——无需安装数据库服务，一个文件就是整个数据库
    #   2. 轻量——毕设数据量（万级评论）完全够用
    #   3. 可移植——整个数据库就是一个 .db 文件，拷贝即迁移
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(DATA_DIR, "weibo.db")}'

    # SQLALCHEMY_TRACK_MODIFICATIONS: 是否追踪对象修改
    #   设为 False 可节省内存，Flask-SQLAlchemy 官方推荐关闭
    SQLALCHEMY_TRACK_MODIFICATIONS = False
