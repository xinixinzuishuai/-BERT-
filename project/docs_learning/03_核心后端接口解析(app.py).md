# 03_核心后端接口解析(app.py)

## 一、Flask应用初始化

### 1. 应用配置

**代码位置：** `app.py` 第 1-25 行

```python
from flask import Flask, request, jsonify, render_template, send_file, make_response, Response, stream_with_context
from flask_cors import CORS
from model_inference import analyzer
from config import Config
from models import db, Comment
from datetime import datetime
from sqlalchemy import func
from urllib.parse import quote
import re
import os
import pandas as pd
import io
import threading
import queue
import jieba.analyse
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)
db.init_app(app)
```

**说明：**
- **Flask**：Web框架，处理HTTP请求和响应
- **CORS**：跨域资源共享，允许前端访问后端API
- **analyzer**：情感分析器实例，用于BERT推理
- **db**：数据库实例，用于数据持久化
- **queue.Queue**：用于流式响应，传递进度信息

### 2. 全局状态管理

**代码位置：** `app.py` 第 27-32 行

```python
spider_state = {
    'is_running': False,
    'status': 'idle',  # idle, waiting_for_login, crawling, analyzing, completed, error
    'message': '',
    'progress': 0
}
```

**说明：**
- `is_running`：爬虫是否正在运行
- `status`：当前状态（空闲/等待登录/爬取中/分析中/完成/错误）
- `message`：状态消息（如"正在爬取第3个话题"）
- `progress`：进度百分比（0-100）

## 二、核心API接口详解

### 1. POST /predict - 单条文本情感预测

**代码位置：** `app.py` 第 36-52 行

```python
@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({
                'error': 'Missing required field: text'
            }), 400
        
        text = data['text']
        result = analyzer.predict(text)
        
        return jsonify({
            'success': True,
            'text': text,
            'sentiment': result
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

**接口说明：**
- **功能：** 对单条文本进行情感分析
- **请求方式：** POST
- **请求参数：** JSON格式，包含 `text` 字段（要分析的文本）
- **返回格式：** JSON格式，包含情感标签和置信度

**请求示例：**
```json
{
    "text": "这个技术太牛了！"
}
```

**返回示例：**
```json
{
    "success": true,
    "text": "这个技术太牛了！",
    "sentiment": {
        "label": "positive",
        "positive": 0.95,
        "neutral": 0.03,
        "negative": 0.02
    }
}
```

**业务逻辑：**
1. 接收前端发送的文本数据
2. 调用 `analyzer.predict(text)` 进行BERT推理
3. 返回情感标签（positive/neutral/negative）和各情感类别的置信度

**使用场景：**
- 用户在首页输入框中输入文本，点击"分析"按钮
- 前端调用此接口，实时显示情感分析结果

---

### 2. GET /health - 健康检查

**代码位置：** `app.py` 第 54-59 行

```python
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'model': Config.BERT_MODEL_NAME
    }), 200
```

**接口说明：**
- **功能：** 检查后端服务和模型是否正常
- **请求方式：** GET
- **请求参数：** 无
- **返回格式：** JSON格式，包含服务状态和模型名称

**返回示例：**
```json
{
    "status": "healthy",
    "model": "bert-base-chinese"
}
```

**使用场景：**
- 前端定期调用此接口，检查后端是否在线
- 用于监控和告警

---

### 3. POST /analyze - 批量分析评论

**代码位置：** `app.py` 第 61-99 行

```python
@app.route('/analyze', methods=['POST'])
def analyze_comments():
    try:
        data = request.get_json()
        
        if not data or 'topic' not in data:
            return jsonify({
                'error': 'Missing required field: topic'
            }), 400
        
        topic = data['topic']
        limit = data.get('limit', 10)
        
        comments = Comment.get_by_topic(topic, limit)
        results = []
        
        for comment in comments:
            if comment.sentiment_label is None:
                sentiment = analyzer.predict(comment.content)
                Comment.update_sentiment(
                    comment.id,
                    sentiment['label'],
                    sentiment[sentiment['label']]
                )
                results.append({
                    'id': comment.id,
                    'content': comment.content,
                    'sentiment': sentiment
                })
            else:
                results.append({
                    'id': comment.id,
                    'content': comment.content,
                    'sentiment': {
                        'label': comment.sentiment_label,
                        'confidence': comment.confidence
                    }
                })
        
        return jsonify({
            'success': True,
            'topic': topic,
            'count': len(results),
            'results': results
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

**接口说明：**
- **功能：** 批量分析指定话题的评论
- **请求方式：** POST
- **请求参数：** JSON格式，包含 `topic`（话题关键词）和 `limit`（可选，限制数量）
- **返回格式：** JSON格式，包含分析结果

**请求示例：**
```json
{
    "topic": "人工智能",
    "limit": 10
}
```

**返回示例：**
```json
{
    "success": true,
    "topic": "人工智能",
    "count": 10,
    "results": [
        {
            "id": 1,
            "content": "这个技术太牛了！",
            "sentiment": {
                "label": "positive",
                "confidence": 0.95
            }
        }
    ]
}
```

**业务逻辑：**
1. 从数据库查询指定话题的评论（最多 `limit` 条）
2. 对于每条评论：
   - 如果已经分析过（`sentiment_label` 不为 None），直接返回结果
   - 如果未分析过，调用BERT模型进行预测，并更新数据库
3. 返回所有评论的情感分析结果

**使用场景：**
- 用户在详情页点击"批量分析"按钮
- 对新爬取的评论进行情感分析

---

### 4. GET /api/sentiment_stats/<topic> - 情感统计

**代码位置：** `app.py` 第 101-155 行

```python
@app.route('/api/sentiment_stats/<topic>', methods=['GET'])
def sentiment_stats(topic):
    try:
        comments = Comment.query.filter_by(topic_keyword=topic).all()
        
        if not comments:
            return jsonify({
                'success': False,
                'error': 'Topic not found'
            }), 404
        
        total = len(comments)
        positive_count = sum(1 for c in comments if c.sentiment_label == 'positive')
        neutral_count = sum(1 for c in comments if c.sentiment_label == 'neutral')
        negative_count = sum(1 for c in comments if c.sentiment_label == 'negative')
        
        pie_data = [
            {'name': '积极', 'value': positive_count},
            {'name': '中性', 'value': neutral_count},
            {'name': '消极', 'value': negative_count}
        ]
        
        sentiment_map = {'positive': 1, 'neutral': 0, 'negative': -1}
        
        time_groups = {}
        for comment in comments:
            if comment.sentiment_label and comment.sentiment_label in sentiment_map:
                hour_key = comment.create_time.strftime('%Y-%m-%d %H:00')
                if hour_key not in time_groups:
                    time_groups[hour_key] = []
                time_groups[hour_key].append(sentiment_map[comment.sentiment_label])
        
        sorted_times = sorted(time_groups.keys())
        line_data = []
        for time_key in sorted_times:
            values = time_groups[time_key]
            avg_sentiment = sum(values) / len(values) if values else 0
            line_data.append({
                'time': time_key,
                'value': round(avg_sentiment, 2)
            })
        
        return jsonify({
            'success': True,
            'topic': topic,
            'total': total,
            'pie_chart': {
                'data': pie_data
            },
            'line_chart': {
                'data': line_data
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

**接口说明：**
- **功能：** 获取指定话题的情感统计数据
- **请求方式：** GET
- **请求参数：** URL路径参数 `topic`（话题关键词）
- **返回格式：** JSON格式，包含饼图数据和折线图数据

**请求示例：**
```
GET /api/sentiment_stats/人工智能
```

**返回示例：**
```json
{
    "success": true,
    "topic": "人工智能",
    "total": 100,
    "pie_chart": {
        "data": [
            {"name": "积极", "value": 60},
            {"name": "中性", "value": 25},
            {"name": "消极", "value": 15}
        ]
    },
    "line_chart": {
        "data": [
            {"time": "2024-03-25 10:00", "value": 0.5},
            {"time": "2024-03-25 11:00", "value": 0.3}
        ]
    }
}
```

**业务逻辑：**
1. 从数据库查询指定话题的所有评论
2. 统计积极、中性、消极评论的数量（用于饼图）
3. 按时间分组，计算每个时间段的平均情感值（用于折线图）
   - 情感值映射：positive=1, neutral=0, negative=-1
   - 计算每个时间段的平均值，范围在 -1 到 1 之间

**SQL查询：**
```python
# 代码位置：app.py 第 103 行
comments = Comment.query.filter_by(topic_keyword=topic).all()
```

**使用场景：**
- 用户访问详情页时，前端自动调用此接口
- 获取数据后，使用ECharts渲染饼图和折线图

---

### 5. GET /api/wordcloud/<topic> - 词云数据

**代码位置：** `app.py` 第 157-182 行

```python
@app.route('/api/wordcloud/<topic>', methods=['GET'])
def wordcloud_stats(topic):
    try:
        comments = Comment.query.filter_by(topic_keyword=topic).all()
        
        if not comments:
            return jsonify({
                'success': False,
                'error': 'Topic not found'
            }), 404
        
        content = " ".join([comment.content for comment in comments])
        
        tags = jieba.analyse.textrank(
            content,
            topK=100,
            withWeight=True,
            allowPOS=('n', 'nr', 'ns', 'vn', 'v')
        )
        
        top_words = [{'name': word, 'value': int(weight * 1000)} for word, weight in tags]
        
        return jsonify({
            'success': True,
            'topic': topic,
            'wordcloud': {
                'data': top_words
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

**接口说明：**
- **功能：** 获取指定话题的词云数据
- **请求方式：** GET
- **请求参数：** URL路径参数 `topic`（话题关键词）
- **返回格式：** JSON格式，包含高频词汇列表

**请求示例：**
```
GET /api/wordcloud/人工智能
```

**返回示例：**
```json
{
    "success": true,
    "topic": "人工智能",
    "wordcloud": {
        "data": [
            {"name": "技术", "value": 850},
            {"name": "创新", "value": 720},
            {"name": "应用", "value": 680}
        ]
    }
}
```

**业务逻辑：**
1. 从数据库查询指定话题的所有评论
2. 将所有评论内容拼接成一个字符串
3. 使用 `jieba.analyse.textrank` 提取高频词汇
   - `topK=100`：提取前100个高频词
   - `allowPOS`：只提取名词、动词等有意义的词
4. 返回词汇列表，包含词名和权重

**使用场景：**
- 用户访问详情页时，前端自动调用此接口
- 获取数据后，使用ECharts渲染词云图

---

### 6. POST /api/run_spider - 运行爬虫（流式响应）

**代码位置：** `app.py` 第 184-450 行

```python
@app.route('/api/run_spider', methods=['POST'])
def run_spider():
    """
    运行爬虫并自动进行情感分析（流式响应）
    支持参数:
    - mode: 'hot' (热搜榜单) 或 'search' (自定义搜索)
    - keyword: 搜索关键词 (仅在 search 模式下有效)
    - topic_count: 爬取的话题数量 (默认: 5, 范围: 1-20, 仅在 hot 模式下有效)
    - count_per_topic: 每个话题爬取的评论数量 (默认: 50, 范围: 10-200)
    - clear_history: 是否在爬取前清空所有历史数据 (默认: False)
    """
    try:
        data = request.get_json()
        mode = data.get('mode', 'hot')
        keyword = data.get('keyword', '').strip()
        topic_count = data.get('topic_count', 5)
        count_per_topic = data.get('count_per_topic', 150)
        clear_history = data.get('clear_history', False)
        
        # 参数验证
        if mode not in ['hot', 'search']:
            return jsonify({
                'success': False,
                'error': '模式必须是 hot 或 search'
            }), 400
        
        if mode == 'search' and not keyword:
            return jsonify({
                'success': False,
                'error': '搜索模式下必须提供关键词'
            }), 400
        
        if topic_count < 1 or topic_count > 20:
            return jsonify({
                'success': False,
                'error': '话题数量必须在 1-20 之间'
            }), 400
        
        if count_per_topic < 10 or count_per_topic > 300:
            return jsonify({
                'success': False,
                'error': '评论数量必须在 10-300 之间'
            }), 400
        
        # 创建队列用于传递进度信息
        progress_queue = queue.Queue()
        
        def send_progress(progress, message, status='processing', error=None):
            """发送进度更新到队列"""
            import json
            
            # 更新全局状态
            spider_state['progress'] = round(progress, 1)
            spider_state['message'] = message
            spider_state['status'] = status
            spider_state['is_running'] = (status not in ['completed', 'error'])
            
            data = {
                'progress': round(progress, 1),
                'message': message,
                'status': status
            }
            if error:
                data['error'] = error
            progress_queue.put(f"data: {json.dumps(data, ensure_ascii=False)}\n\n")
        
        def spider_task():
            """爬虫任务（在单独线程中运行）"""
            try:
                from weibo_spider import WeiboSpider
                from model_inference import SentimentAnalyzer
                
                # 如果需要清空历史数据
                if clear_history:
                    send_progress(0, "正在清空所有历史数据...")
                    try:
                        with app.app_context():
                            deleted_count = Comment.query.delete()
                            db.session.commit()
                            send_progress(0, f"已清空 {deleted_count} 条历史数据")
                    except Exception as e:
                        send_progress(0, f"清空历史数据失败: {str(e)}", status='error', error=str(e))
                        progress_queue.put(None)
                        return
                
                # 创建爬虫（强制显示浏览器窗口，方便扫码登录）
                spider = WeiboSpider(headless=False)
                
                # 根据模式选择爬取方式
                if mode == 'search':
                    # 搜索模式：直接使用关键词
                    send_progress(0, f"开始搜索关键词：{keyword}")
                    total_saved = spider.crawl_single_topic(
                        keyword,
                        count_per_topic,
                        progress_callback=send_progress
                    )
                else:
                    # 热搜模式：获取热搜榜
                    send_progress(0, "开始获取微博热搜榜...")
                    total_saved = spider.crawl_hot_topics(
                        count_per_topic, 
                        topic_count,
                        progress_callback=send_progress
                    )
                
                # 阶段3: BERT分析 (60-90%)
                send_progress(60, f"爬取完成！共获取 {total_saved} 条评论，开始情感分析...")
                
                # 创建情感分析器
                sentiment_analyzer = SentimentAnalyzer()
                
                # 运行情感分析（带进度回调）
                analyzed_count = sentiment_analyzer.batch_analyze_database(
                    batch_size=32,
                    progress_callback=send_progress
                )
                
                # 阶段4: 完成 (100%)
                send_progress(100, f"分析完成！共处理 {total_saved} 条评论，其中 {analyzed_count} 条已完成情感标注。", status='completed')
                
                # 发送结束信号
                progress_queue.put(None)
                
            except Exception as e:
                import traceback
                error_msg = f"爬虫任务出错: {str(e)}"
                send_progress(0, error_msg, status='error', error=error_msg)
                progress_queue.put(None)
        
        # 启动爬虫线程
        thread = threading.Thread(target=spider_task)
        thread.start()
        
        # 返回流式响应
        def generate():
            while True:
                data = progress_queue.get()
                if data is None:
                    break
                yield data
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream'
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

**接口说明：**
- **功能：** 运行爬虫并自动进行情感分析（流式响应）
- **请求方式：** POST
- **请求参数：** JSON格式
  - `mode`：'hot'（热搜榜单）或 'search'（自定义搜索）
  - `keyword`：搜索关键词（仅在 search 模式下有效）
  - `topic_count`：爬取的话题数量（默认: 5, 范围: 1-20）
  - `count_per_topic`：每个话题爬取的评论数量（默认: 150, 范围: 10-300）
  - `clear_history`：是否在爬取前清空所有历史数据（默认: False）
- **返回格式：** Server-Sent Events (SSE) 流式响应

**请求示例：**
```json
{
    "mode": "hot",
    "topic_count": 5,
    "count_per_topic": 150,
    "clear_history": false
}
```

**流式响应示例：**
```
data: {"progress": 0, "message": "开始获取微博热搜榜...", "status": "processing"}

data: {"progress": 10, "message": "正在爬取第1个话题：人工智能", "status": "processing"}

data: {"progress": 60, "message": "爬取完成！共获取 750 条评论，开始情感分析...", "status": "processing"}

data: {"progress": 100, "message": "分析完成！共处理 750 条评论，其中 750 条已完成情感标注。", "status": "completed"}
```

**业务逻辑：**
1. 验证请求参数（模式、关键词、话题数量、评论数量）
2. 创建队列用于传递进度信息
3. 在单独线程中执行爬虫任务：
   - 如果需要清空历史数据，先清空数据库
   - 创建 `WeiboSpider` 实例
   - 根据模式（热搜/搜索）执行不同的爬取逻辑
   - 调用 `SentimentAnalyzer` 进行批量情感分析
4. 通过队列实时推送进度信息
5. 返回 SSE 流式响应，前端实时接收进度

**SQL查询：**
```python
# 代码位置：app.py 第 300 行
deleted_count = Comment.query.delete()
db.session.commit()
```

**使用场景：**
- 用户在首页点击"开始爬取"按钮
- 前端调用此接口，实时显示爬虫进度

---

### 7. GET /export/<topic>/<format> - 导出数据

**代码位置：** `app.py` 第 210-310 行

```python
@app.route('/export/<topic>/<format>', methods=['GET'])
def export_data(topic, format):
    """
    导出指定话题的分析结果
    
    Args:
        topic: 话题关键词
        format: 导出格式 (excel 或 csv)
    """
    try:
        comments = Comment.query.filter_by(topic_keyword=topic).all()
        
        if not comments:
            return jsonify({
                'success': False,
                'error': 'Topic not found'
            }), 404
        
        data = []
        for comment in comments:
            data.append({
                'ID': comment.id,
                '话题': comment.topic_keyword,
                '评论内容': comment.content,
                '发布时间': comment.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                '情感标签': comment.sentiment_label if comment.sentiment_label else '未分析',
                '置信度': round(comment.confidence, 4) if comment.confidence else 0,
                '手动标注': comment.manual_label if comment.manual_label else '无'
            })
        
        df = pd.DataFrame(data)
        
        sentiment_map = {'positive': '积极', 'neutral': '中性', 'negative': '消极'}
        df['情感标签'] = df['情感标签'].map(lambda x: sentiment_map.get(x, x))
        df['手动标注'] = df['手动标注'].map(lambda x: sentiment_map.get(x, x))
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"weibo_sentiment_{topic}_{timestamp}"
        
        if format.lower() == 'csv':
            output = io.BytesIO()
            output.write(b'\xef\xbb\xbf')
            csv_content = df.to_csv(index=False, encoding='utf-8')
            output.write(csv_content.encode('utf-8'))
            output.seek(0)
            
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv; charset=utf-8'
            encoded_filename = quote(f"{filename}.csv")
            response.headers['Content-Disposition'] = f"attachment; filename*=utf-8''{encoded_filename}"
            return response
        
        elif format.lower() == 'excel':
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='情感分析数据')
                
                worksheet = writer.sheets['情感分析数据']
                
                header_fill = PatternFill(start_color='667eea', end_color='667eea', fill_type='solid')
                header_font = Font(bold=True, color='FFFFFF', size=12)
                
                for col_num, column in enumerate(df.columns, 1):
                    cell = worksheet.cell(row=1, column=col_num)
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal='center', vertical='center')
                    
                    column_letter = get_column_letter(col_num)
                    max_length = max(
                        df[column].astype(str).apply(len).max(),
                        len(str(column))
                    )
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                for row_num, row_data in enumerate(df.itertuples(index=False), 2):
                    for col_num, value in enumerate(row_data, 1):
                        cell = worksheet.cell(row=row_num, column=col_num)
                        cell.alignment = Alignment(wrap_text=True, vertical='top')
                        
                        if col_num == 5:
                            if value == '积极':
                                cell.fill = PatternFill(start_color='d4edda', end_color='d4edda', fill_type='solid')
                            elif value == '消极':
                                cell.fill = PatternFill(start_color='f8d7da', end_color='f8d7da', fill_type='solid')
                            elif value == '中性':
                                cell.fill = PatternFill(start_color='fff3cd', end_color='fff3cd', fill_type='solid')
            
            output.seek(0)
            
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            encoded_filename = quote(f"{filename}.xlsx")
            response.headers['Content-Disposition'] = f"attachment; filename*=utf-8''{encoded_filename}"
            return response
        
        else:
            return jsonify({
                'success': False,
                'error': 'Unsupported format. Use "excel" or "csv"'
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

**接口说明：**
- **功能：** 导出指定话题的分析结果
- **请求方式：** GET
- **请求参数：** URL路径参数 `topic`（话题关键词）和 `format`（导出格式：excel 或 csv）
- **返回格式：** 文件下载（CSV 或 Excel）

**请求示例：**
```
GET /export/人工智能/csv
GET /export/人工智能/excel
```

**业务逻辑：**
1. 从数据库查询指定话题的所有评论
2. 将评论数据转换为 DataFrame
3. 根据格式（CSV/Excel）生成文件
4. 返回文件下载响应

**SQL查询：**
```python
# 代码位置：app.py 第 220 行
comments = Comment.query.filter_by(topic_keyword=topic).all()
```

**使用场景：**
- 用户在详情页点击"导出 CSV"或"导出 Excel"按钮
- 下载分析结果用于报告或进一步分析

---

## 三、答辩常见问题

### Q1: 你的系统有哪些核心接口？分别起什么作用？
**标准回答：**
我的系统有7个核心接口。`/predict`用于单条文本情感分析，`/health`用于健康检查，`/analyze`用于批量分析评论，`/api/sentiment_stats`用于获取情感统计数据（饼图和折线图），`/api/wordcloud`用于获取词云数据，`/api/run_spider`用于运行爬虫（流式响应），`/export`用于导出数据。这些接口覆盖了系统的所有核心功能：数据采集、情感分析、可视化展示、数据导出。

### Q2: 流式响应是怎么实现的？为什么要用流式响应？
**标准回答：**
流式响应使用的是Server-Sent Events (SSE)技术。在`/api/run_spider`接口中，我创建了一个队列（queue.Queue），爬虫任务在后台线程中运行，每完成一个阶段就往队列里放入进度信息。主线程通过`stream_with_context`不断从队列中取出数据，实时推送到前端。使用流式响应的好处是用户可以实时看到爬虫进度，而不是一直等待直到任务完成，用户体验更好。

### Q3: 你的接口如何处理中文文件名的？
**标准回答：**
在导出接口中，我使用了`urllib.parse.quote`对中文文件名进行URL编码，然后使用RFC 5987标准的`filename*=utf-8''`格式设置Content-Disposition响应头。这样可以确保中文文件名在所有浏览器中都能正确显示。同时，对于CSV文件，我还在文件开头添加了UTF-8 BOM（b'\xef\xbb\xbf'），防止Excel打开时出现乱码。

### Q4: 你的爬虫接口是如何保证数据质量的？
**标准回答：**
我的爬虫接口在多个层面做了优化。第一，实现了"保量爬取"逻辑，确保能够获取到目标数量的评论，不会因为广告或解析失败导致数量不足。第二，设置了防死循环安全阀，最多滚动20次，连续6次获取不到新数据就强制退出，防止程序卡死。第三，实现了去重逻辑，基于文本内容过滤重复评论。第四，爬取完成后自动调用BERT模型进行情感分析，确保数据的完整性和可用性。
