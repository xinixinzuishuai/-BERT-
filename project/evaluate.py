import time
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from model_inference import SentimentAnalyzer
from models import db, Comment
from db_init import app

class ModelEvaluator:
    def __init__(self):
        self.analyzer = SentimentAnalyzer()
        self.device = self.analyzer.device
    
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
    
    def _create_test_data(self):
        """
        创建测试数据，为部分评论添加手动标注
        """
        with app.app_context():
            comments = Comment.query.filter(
                Comment.sentiment_label.isnot(None)
            ).limit(100).all()
            
            for comment in comments:
                comment.manual_label = comment.sentiment_label
            
            db.session.commit()
            print(f"已为 {len(comments)} 条评论添加手动标注")
    
    def generate_evaluation_report(self, output_file='evaluation_report.txt'):
        """
        生成完整的评估报告
        
        Args:
            output_file: 输出文件路径
        """
        print("\n" + "="*70)
        print("生成评估报告")
        print("="*70)
        
        latency_results = self.measure_latency()
        accuracy_results = self.evaluate_accuracy()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("BERT 情感分析模型评估报告\n")
            f.write("="*70 + "\n\n")
            
            f.write("1. 性能测试结果\n")
            f.write("-"*70 + "\n")
            f.write(f"设备: {self.device}\n\n")
            
            f.write(f"{'数据量':<10} {'平均耗时(s)':<15} {'单样本(ms)':<15} {'吞吐量(样本/s)':<20}\n")
            f.write("-"*70 + "\n")
            for size in sorted(latency_results.keys()):
                r = latency_results[size]
                f.write(f"{size:<10} {r['avg_latency']:<15.4f} {r['avg_per_sample']*1000:<15.2f} {r['throughput']:<20.2f}\n")
            
            f.write("\n2. 准确率评估结果\n")
            f.write("-"*70 + "\n")
            if accuracy_results:
                f.write(f"总体准确率: {accuracy_results['accuracy']*100:.2f}%\n\n")
                f.write("分类报告:\n")
                f.write(accuracy_results['classification_report'])
                f.write("\n混淆矩阵:\n")
                cm = accuracy_results['confusion_matrix']
                f.write("                预测标签\n")
                f.write("                negative  neutral  positive\n")
                labels = ['negative', 'neutral', 'positive']
                for i, label in enumerate(labels):
                    f.write(f"真实 {label:>8}  {cm[i][0]:>8}  {cm[i][1]:>8}  {cm[i][2]:>8}\n")
            
            f.write("\n" + "="*70 + "\n")
            f.write(f"报告生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*70 + "\n")
        
        print(f"\n评估报告已保存到: {output_file}")
        print("="*70)

def main():
    evaluator = ModelEvaluator()
    
    print("\n选择评估模式:")
    print("1. 性能测试（推理耗时）")
    print("2. 准确率评估")
    print("3. 生成完整评估报告")
    print("4. 全部测试")
    
    choice = input("\n请输入选项 (1-4): ").strip()
    
    if choice == '1':
        evaluator.measure_latency()
    elif choice == '2':
        evaluator.evaluate_accuracy()
    elif choice == '3':
        evaluator.generate_evaluation_report()
    elif choice == '4':
        evaluator.measure_latency()
        evaluator.evaluate_accuracy()
        evaluator.generate_evaluation_report()
    else:
        print("无效选项")

if __name__ == '__main__':
    main()
