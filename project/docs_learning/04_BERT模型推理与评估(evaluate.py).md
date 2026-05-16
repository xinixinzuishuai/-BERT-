# 04_BERT模型推理与评估(evaluate.py)

## 一、模型推理概述

本系统使用 **BERT（Bidirectional Encoder Representations from Transformers）** 模型进行情感分析。BERT 是一种基于 Transformer 架构的预训练语言模型，能够理解上下文信息，在情感分析任务中表现优异。

### 模型选择

**代码位置：** `config.py` 和 `model_inference.py`

```python
# config.py
class Config:
    BERT_MODEL_NAME = 'bert-base-chinese'
    
# model_inference.py
from transformers import BertTokenizer, BertForSequenceClassification
```

**说明：**
- **模型名称：** `bert-base-chinese`（哈工大讯飞联合实验室的中文BERT模型）
- **模型架构：** 12层Transformer，768隐藏层维度，12个注意力头
- **训练数据：** 大规模中文语料
- **任务类型：** 序列分类（Sequence Classification）

## 二、模型推理流程

### 1. 模型加载

**代码位置：** `model_inference.py` 第 20-40 行

```python
class SentimentAnalyzer:
    def __init__(self, model_name=Config.BERT_MODEL_NAME):
        self.model_name = model_name
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # 加载分词器
        self.tokenizer = BertTokenizer.from_pretrained(model_name)
        
        # 加载模型
        self.model = BertForSequenceClassification.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()
        
        print(f"模型加载完成: {model_name}")
        print(f"设备: {self.device}")
```

**详细说明：**
1. **设备选择：** 检测是否有GPU，如果有则使用GPU加速，否则使用CPU
2. **分词器加载：** 加载 `BertTokenizer`，用于将文本转换为模型可理解的token
3. **模型加载：** 加载 `BertForSequenceClassification`，这是一个预训练的序列分类模型
4. **模型评估模式：** 调用 `model.eval()`，关闭 Dropout 和 BatchNorm，确保推理结果稳定

**关键变量：**
- `self.device`：计算设备（cuda 或 cpu）
- `self.tokenizer`：分词器实例
- `self.model`：BERT模型实例

---

### 2. 单条文本推理

**代码位置：** `model_inference.py` 第 42-70 行

```python
def predict(self, text):
    """
    对单条文本进行情感分析
    
    Args:
        text: 要分析的文本
        
    Returns:
        dict: 包含情感标签和置信度的字典
    """
    # 文本预处理
    text = text.strip()
    if not text:
        return {
            'label': 'neutral',
            'positive': 0.33,
            'neutral': 0.34,
            'negative': 0.33
        }
    
    # 分词
    inputs = self.tokenizer(
        text,
        return_tensors='pt',
        padding=True,
        truncation=True,
        max_length=512
    )
    
    # 将输入移动到设备
    inputs = {k: v.to(self.device) for k, v in inputs.items()}
    
    # 模型推理
    with torch.no_grad():
        outputs = self.model(**inputs)
    
    # 获取预测结果
    logits = outputs.logits
    probabilities = torch.softmax(logits, dim=-1)
    probabilities = probabilities.cpu().numpy()[0]
    
    # 映射到情感标签
    label_map = {0: 'negative', 1: 'neutral', 2: 'positive'}
    predicted_label = label_map[probabilities.argmax()]
    
    return {
        'label': predicted_label,
        'negative': float(probabilities[0]),
        'neutral': float(probabilities[1]),
        'positive': float(probabilities[2])
    }
```

**详细说明：**

#### 步骤1：文本预处理
- 去除首尾空格
- 检查文本是否为空，如果为空返回中性情感

#### 步骤2：分词（Tokenization）
```python
inputs = self.tokenizer(
    text,
    return_tensors='pt',  # 返回PyTorch张量
    padding=True,         # 填充到相同长度
    truncation=True,      # 截断超过最大长度的文本
    max_length=512        # 最大长度512个token
)
```

**作用：** 将文本转换为模型可理解的数字序列
- `input_ids`：文本的token ID序列
- `attention_mask`：标记哪些token是有效的（1）哪些是填充的（0）

#### 步骤3：移动到设备
```python
inputs = {k: v.to(self.device) for k, v in inputs.items()}
```

**作用：** 将输入数据移动到GPU（如果可用），加速推理

#### 步骤4：模型推理
```python
with torch.no_grad():
    outputs = self.model(**inputs)
```

**作用：** 
- `torch.no_grad()`：关闭梯度计算，减少内存占用，加速推理
- `self.model(**inputs)`：前向传播，获取模型输出

#### 步骤5：获取预测结果
```python
logits = outputs.logits  # 原始输出（未归一化）
probabilities = torch.softmax(logits, dim=-1)  # 归一化为概率
probabilities = probabilities.cpu().numpy()[0]  # 转换为numpy数组
```

**作用：**
- `logits`：模型输出的原始分数（3个类别，每个一个分数）
- `softmax`：将分数转换为概率（0-1之间，总和为1）
- `argmax`：找到概率最大的类别作为预测结果

#### 步骤6：映射到情感标签
```python
label_map = {0: 'negative', 1: 'neutral', 2: 'positive'}
predicted_label = label_map[probabilities.argmax()]
```

**作用：** 将模型输出的类别索引（0/1/2）映射到情感标签（negative/neutral/positive）

**返回结果示例：**
```json
{
    "label": "positive",
    "negative": 0.05,
    "neutral": 0.15,
    "positive": 0.80
}
```

---

### 3. 批量推理

**代码位置：** `model_inference.py` 第 72-100 行

```python
def batch_predict(self, texts):
    """
    批量推理
    
    Args:
        texts: 文本列表
        
    Returns:
        list: 预测结果列表
    """
    if not texts:
        return []
    
    # 分词
    inputs = self.tokenizer(
        texts,
        return_tensors='pt',
        padding=True,
        truncation=True,
        max_length=512
    )
    
    # 移动到设备
    inputs = {k: v.to(self.device) for k, v in inputs.items()}
    
    # 批量推理
    with torch.no_grad():
        outputs = self.model(**inputs)
    
    # 获取预测结果
    logits = outputs.logits
    probabilities = torch.softmax(logits, dim=-1)
    probabilities = probabilities.cpu().numpy()
    
    # 映射到情感标签
    label_map = {0: 'negative', 1: 'neutral', 2: 'positive'}
    results = []
    
    for i in range(len(texts)):
        predicted_label = label_map[probabilities[i].argmax()]
        results.append({
            'label': predicted_label,
            'negative': float(probabilities[i][0]),
            'neutral': float(probabilities[i][1]),
            'positive': float(probabilities[i][2])
        })
    
    return results
```

**详细说明：**
- **批量分词：** 一次性处理多条文本，提高效率
- **批量推理：** 模型一次处理一个batch，充分利用GPU并行计算能力
- **结果解析：** 遍历batch中的每个样本，提取预测结果

**优势：**
- 比单条推理快很多（充分利用GPU并行计算）
- 减少模型调用次数，降低延迟

---

### 4. 批量数据库分析

**代码位置：** `model_inference.py` 第 102-150 行

```python
def batch_analyze_database(self, batch_size=32, progress_callback=None):
    """
    批量分析数据库中的未分析评论
    
    Args:
        batch_size: 批量大小
        progress_callback: 进度回调函数
        
    Returns:
        int: 分析的评论数量
    """
    from models import Comment, db
    from app import app
    
    with app.app_context():
        # 查询未分析的评论
        unanalyzed_comments = Comment.get_unanalyzed_comments()
        
        if not unanalyzed_comments:
            return 0
        
        total = len(unanalyzed_comments)
        analyzed_count = 0
        
        # 分批处理
        for i in range(0, total, batch_size):
            batch = unanalyzed_comments[i:i+batch_size]
            texts = [comment.content for comment in batch]
            
            # 批量推理
            results = self.batch_predict(texts)
            
            # 更新数据库
            for comment, result in zip(batch, results):
                Comment.update_sentiment(
                    comment.id,
                    result['label'],
                    result[result['label']]
                )
                analyzed_count += 1
            
            # 进度回调
            if progress_callback:
                progress = (analyzed_count / total) * 30 + 60  # 60-90%的进度
                progress_callback(progress, f"已分析 {analyzed_count}/{total} 条评论")
        
        return analyzed_count
```

**详细说明：**

#### 步骤1：查询未分析的评论
```python
unanalyzed_comments = Comment.get_unanalyzed_comments()
```

**作用：** 从数据库查询所有 `sentiment_label` 为 `None` 的评论

#### 步骤2：分批处理
```python
for i in range(0, total, batch_size):
    batch = unanalyzed_comments[i:i+batch_size]
    texts = [comment.content for comment in batch]
```

**作用：** 将评论分成多个batch，每个batch包含 `batch_size` 条评论（默认32条）

#### 步骤3：批量推理
```python
results = self.batch_predict(texts)
```

**作用：** 对当前batch的评论进行批量推理

#### 步骤4：更新数据库
```python
for comment, result in zip(batch, results):
    Comment.update_sentiment(
        comment.id,
        result['label'],
        result[result['label']]
    )
```

**作用：** 将推理结果更新到数据库中

#### 步骤5：进度回调
```python
if progress_callback:
    progress = (analyzed_count / total) * 30 + 60  # 60-90%的进度
    progress_callback(progress, f"已分析 {analyzed_count}/{total} 条评论")
```

**作用：** 实时推送进度信息到前端（60-90%的进度区间）

**关键变量：**
- `batch_size`：批量大小（默认32），影响推理速度和内存占用
- `analyzed_count`：已分析的评论数量
- `progress_callback`：进度回调函数，用于实时推送进度

---

## 三、模型评估

### 1. 评估类初始化

**代码位置：** `evaluate.py` 第 10-15 行

```python
class ModelEvaluator:
    def __init__(self):
        self.analyzer = SentimentAnalyzer()
        self.device = self.analyzer.device
```

**说明：**
- 创建 `SentimentAnalyzer` 实例
- 记录计算设备（GPU/CPU）

---

### 2. 性能测试（推理耗时）

**代码位置：** `evaluate.py` 第 17-85 行

```python
def measure_latency(self, sample_sizes=[100, 500, 1000], num_runs=3):
    """
    测量模型在不同数据量下的平均推理耗时
    
    Args:
        sample_sizes: 测试的数据量列表
        num_runs: 每个数据量重复运行的次数
    """
    print("="*70)
    print("BERT 模型性能评估 - 推理耗时测试")
    print("="*70)
    print(f"设备: {self.device}")
    print(f"测试数据量: {sample_sizes}")
    print(f"每个数据量重复次数: {num_runs}")
    print("-"*70)
    
    with app.app_context():
        all_comments = Comment.query.filter(Comment.sentiment_label.isnot(None)).all()
        
        if len(all_comments) < max(sample_sizes):
            print(f"警告: 数据库中只有 {len(all_comments)} 条评论，少于最大测试量 {max(sample_sizes)}")
            max_available = len(all_comments)
            sample_sizes = [s for s in sample_sizes if s <= max_available]
            if not sample_sizes:
                print("错误: 数据不足，无法进行测试")
                return
        
        results = {}
        
        for size in sample_sizes:
            print(f"\n测试数据量: {size} 条")
            print("-"*70)
            
            latencies = []
            
            for run in range(1, num_runs + 1):
                sample_comments = np.random.choice(all_comments, size=size, replace=False)
                texts = [comment.content for comment in sample_comments]
                
                start_time = time.time()
                results_batch = self.analyzer.batch_predict(texts)
                end_time = time.time()
                
                latency = end_time - start_time
                latencies.append(latency)
                
                avg_latency_per_sample = latency / size
                
                print(f"  第 {run} 次运行: {latency:.4f} 秒 ({avg_latency_per_sample*1000:.2f} ms/样本)")
            
            avg_latency = np.mean(latencies)
            std_latency = np.std(latencies)
            min_latency = np.min(latencies)
            max_latency = np.max(latencies)
            avg_per_sample = avg_latency / size
            
            results[size] = {
                'avg_latency': avg_latency,
                'std_latency': std_latency,
                'min_latency': min_latency,
                'max_latency': max_latency,
                'avg_per_sample': avg_per_sample,
                'throughput': size / avg_latency
            }
            
            print(f"\n  平均耗时: {avg_latency:.4f} 秒 (±{std_latency:.4f})")
            print(f"  单样本平均: {avg_per_sample*1000:.2f} ms")
            print(f"  吞吐量: {size/avg_latency:.2f} 样本/秒")
            print(f"  最小/最大: {min_latency:.4f}s / {max_latency:.4f}s")
        
        print("\n" + "="*70)
        print("性能测试总结")
        print("="*70)
        print(f"{'数据量':<10} {'平均耗时(s)':<15} {'单样本(ms)':<15} {'吞吐量(样本/s)':<20}")
        print("-"*70)
        for size in sorted(results.keys()):
            r = results[size]
            print(f"{size:<10} {r['avg_latency']:<15.4f} {r['avg_per_sample']*1000:<15.2f} {r['throughput']:<20.2f}")
        print("="*70)
        
        return results
```

**详细说明：**

#### 步骤1：查询已分析的评论
```python
all_comments = Comment.query.filter(Comment.sentiment_label.isnot(None)).all()
```

**作用：** 从数据库查询所有已分析的评论，用于性能测试

#### 步骤2：随机采样
```python
sample_comments = np.random.choice(all_comments, size=size, replace=False)
texts = [comment.content for comment in sample_comments]
```

**作用：** 从所有评论中随机抽取指定数量的样本

#### 步骤3：测量推理耗时
```python
start_time = time.time()
results_batch = self.analyzer.batch_predict(texts)
end_time = time.time()
latency = end_time - start_time
```

**作用：** 记录推理开始和结束时间，计算耗时

#### 步骤4：计算统计指标
```python
avg_latency = np.mean(latencies)  # 平均耗时
std_latency = np.std(latencies)   # 标准差
min_latency = np.min(latencies)   # 最小耗时
max_latency = np.max(latencies)   # 最大耗时
throughput = size / avg_latency   # 吞吐量（样本/秒）
```

**作用：** 计算多个统计指标，全面评估性能

**输出示例：**
```
测试数据量: 100 条
----------------------------------------------------------------------
  第 1 次运行: 2.3456 秒 (23.46 ms/样本)
  第 2 次运行: 2.2891 秒 (22.89 ms/样本)
  第 3 次运行: 2.3123 秒 (23.12 ms/样本)

  平均耗时: 2.3157 秒 (±0.0234)
  单样本平均: 23.16 ms
  吞吐量: 43.17 样本/秒
  最小/最大: 2.2891s / 2.3456s
```

---

### 3. 准确率评估

**代码位置：** `evaluate.py` 第 87-145 行

```python
def evaluate_accuracy(self, test_size=200):
    """
    评估模型准确率，对比手动标注和模型预测
    
    Args:
        test_size: 测试样本数量
    """
    print("\n" + "="*70)
    print("BERT 模型准确率评估")
    print("="*70)
    
    with app.app_context():
        comments = Comment.query.filter(
            Comment.sentiment_label.isnot(None),
            Comment.manual_label.isnot(None)
        ).all()
        
        if len(comments) == 0:
            print("没有找到同时包含模型预测和手动标注的数据")
            print("正在创建测试数据...")
            self._create_test_data()
            comments = Comment.query.filter(
                Comment.sentiment_label.isnot(None),
                Comment.manual_label.isnot(None)
            ).all()
        
        if len(comments) == 0:
            print("错误: 无法创建测试数据")
            return None
        
        if len(comments) > test_size:
            comments = np.random.choice(comments, size=test_size, replace=False)
        
        print(f"测试样本数: {len(comments)}")
        print("-"*70)
        
        y_true = []
        y_pred = []
        
        for comment in comments:
            y_true.append(comment.manual_label)
            y_pred.append(comment.sentiment_label)
        
        accuracy = accuracy_score(y_true, y_pred)
        
        print(f"\n总体准确率: {accuracy*100:.2f}%")
        print("\n分类报告:")
        print("-"*70)
        
        report = classification_report(
            y_true, 
            y_pred, 
            target_names=['negative', 'neutral', 'positive'],
            digits=4
        )
        print(report)
        
        print("\n混淆矩阵:")
        print("-"*70)
        cm = confusion_matrix(y_true, y_pred, labels=['negative', 'neutral', 'positive'])
        print("                预测标签")
        print("                negative  neutral  positive")
        labels = ['negative', 'neutral', 'positive']
        for i, label in enumerate(labels):
            print(f"真实 {label:>8}  {cm[i][0]:>8}  {cm[i][1]:>8}  {cm[i][2]:>8}")
        
        print("="*70)
        
        return {
            'accuracy': accuracy,
            'classification_report': report,
            'confusion_matrix': cm
        }
```

**详细说明：**

#### 步骤1：查询测试数据
```python
comments = Comment.query.filter(
    Comment.sentiment_label.isnot(None),
    Comment.manual_label.isnot(None)
).all()
```

**作用：** 查询同时包含模型预测和手动标注的评论

**关键变量：**
- `y_true`：真实标签（手动标注）
- `y_pred`：预测标签（模型预测）

#### 步骤2：创建测试数据（如果需要）
```python
if len(comments) == 0:
    print("正在创建测试数据...")
    self._create_test_data()
```

**作用：** 如果没有测试数据，自动创建（将模型预测结果复制到手动标注字段）

#### 步骤3：计算准确率
```python
accuracy = accuracy_score(y_true, y_pred)
```

**作用：** 计算模型预测的准确率（预测正确的样本数 / 总样本数）

#### 步骤4：生成分类报告
```python
report = classification_report(
    y_true, 
    y_pred, 
    target_names=['negative', 'neutral', 'positive'],
    digits=4
)
```

**作用：** 生成详细的分类报告，包括：
- **Precision（精确率）：** 预测为正例的样本中，真正为正例的比例
- **Recall（召回率）：** 真正为正例的样本中，预测为正例的比例
- **F1-score：** 精确率和召回率的调和平均数
- **Support：** 每个类别的样本数量

**输出示例：**
```
分类报告:
----------------------------------------------------------------------
              precision    recall  f1-score   support

    negative     0.9231    0.8889    0.9057        45
     neutral     0.8667    0.8667    0.8667        30
    positive     0.9286    0.9500    0.9392        40

    accuracy                         0.9050       115
   macro avg     0.9061    0.9019    0.9039       115
weighted avg     0.9049    0.9050    0.9048       115
```

#### 步骤5：生成混淆矩阵
```python
cm = confusion_matrix(y_true, y_pred, labels=['negative', 'neutral', 'positive'])
```

**作用：** 生成混淆矩阵，展示模型在每个类别上的表现

**输出示例：**
```
混淆矩阵:
----------------------------------------------------------------------
                预测标签
                negative  neutral  positive
真实  negative        40        3        2
     neutral          2       26        2
    positive          1        1       38
```

**解读：**
- 真实为 `negative` 的45条评论中，模型预测正确40条，误判为 `neutral` 3条，误判为 `positive` 2条
- 真实为 `neutral` 的30条评论中，模型预测正确26条，误判为 `negative` 2条，误判为 `positive` 2条
- 真实为 `positive` 的40条评论中，模型预测正确38条，误判为 `negative` 1条，误判为 `neutral` 1条

---

## 四、关键变量说明

### 1. y_true（真实标签）

**定义：** 人工标注的情感标签列表

**代码位置：** `evaluate.py` 第 128 行

```python
y_true = []
for comment in comments:
    y_true.append(comment.manual_label)
```

**作用：** 存储真实标签，用于计算准确率

**取值范围：** `['negative', 'neutral', 'positive']`

---

### 2. y_pred（预测标签）

**定义：** 模型预测的情感标签列表

**代码位置：** `evaluate.py` 第 129 行

```python
y_pred = []
for comment in comments:
    y_pred.append(comment.sentiment_label)
```

**作用：** 存储预测标签，用于计算准确率

**取值范围：** `['negative', 'neutral', 'positive']`

---

### 3. probabilities（概率分布）

**定义：** 模型输出的情感概率分布

**代码位置：** `model_inference.py` 第 62 行

```python
probabilities = torch.softmax(logits, dim=-1)
probabilities = probabilities.cpu().numpy()[0]
```

**作用：** 存储每个情感类别的概率

**取值范围：** 0-1之间的浮点数，总和为1

**示例：** `[0.05, 0.15, 0.80]`（negative: 5%, neutral: 15%, positive: 80%）

---

### 4. logits（原始输出）

**定义：** 模型输出的原始分数（未归一化）

**代码位置：** `model_inference.py` 第 61 行

```python
logits = outputs.logits
```

**作用：** 存储模型输出的原始分数

**取值范围：** 任意实数（负无穷到正无穷）

**示例：** `[-2.3, 0.5, 3.1]`（negative: -2.3, neutral: 0.5, positive: 3.1）

---

## 五、答辩常见问题

### Q1: 你的模型是如何加载的？为什么选择BERT？
**标准回答：**
我使用了Hugging Face的Transformers库来加载预训练的BERT模型（bert-base-chinese）。在`model_inference.py`中，我封装了一个`SentimentAnalyzer`类，负责模型的加载、推理和结果解析。选择BERT是因为它是一种基于Transformer架构的预训练语言模型，能够理解上下文信息，在情感分析任务中表现优异。而且BERT有丰富的中文预训练模型，可以直接使用，不需要从头训练。

### Q2: y_true和y_pred分别代表什么？如何计算准确率？
**标准回答：**
`y_true`是真实标签，也就是人工标注的情感标签；`y_pred`是预测标签，也就是模型预测的情感标签。准确率的计算公式是：预测正确的样本数除以总样本数。在代码中，我使用sklearn的`accuracy_score(y_true, y_pred)`函数来计算准确率。比如有100条评论，模型预测正确了90条，那么准确率就是90%。

### Q3: 你的模型推理流程是怎样的？为什么需要分词？
**标准回答：**
我的模型推理流程分为5个步骤：1）文本预处理，去除空格；2）分词，使用BertTokenizer将文本转换为token ID序列；3）移动到设备，将输入数据移动到GPU（如果可用）；4）模型推理，调用BERT模型进行前向传播；5）结果解析，使用softmax将输出转换为概率，找到概率最大的类别作为预测结果。分词是必要的，因为BERT模型只能理解数字序列，不能直接处理文本，所以需要先将文本转换为token ID。

### Q4: 混淆矩阵是什么？如何解读？
**标准回答：**
混淆矩阵是一个表格，用于评估分类模型的性能。它展示了模型在每个类别上的表现，包括预测正确和错误的数量。在我的系统中，混淆矩阵是一个3x3的表格，行表示真实标签，列表示预测标签。比如第一行第一列的数字40表示真实为negative的评论中，模型预测为negative的有40条（预测正确）；第一行第二列的数字3表示真实为negative的评论中，模型误判为neutral的有3条（预测错误）。通过混淆矩阵，我可以清楚地看到模型在哪些类别上容易出错。
