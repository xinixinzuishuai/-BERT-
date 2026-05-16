from modelscope import snapshot_download

print("正在开始下载模型，请耐心等待...")
# 下载阿里 StructBERT 情感分析模型
model_dir = snapshot_download('iic/nlp_structbert_sentiment-classification_chinese-base')

print("\n" + "="*50)
print(f"✅ 模型下载完成！路径位于: {model_dir}")
print("="*50)