import random
from datetime import datetime, timedelta
from models import db, Comment
from db_init import app

def adjust_sentiment_distribution(topic_keyword=None, target_distribution=None):
    """
    调整情感分布，确保三种情感都有合理的数量
    
    Args:
        topic_keyword: 指定话题，None表示所有话题
        target_distribution: 目标分布 {'positive': 0.4, 'neutral': 0.3, 'negative': 0.3}
    """
    if target_distribution is None:
        target_distribution = {
            'positive': 0.4,
            'neutral': 0.3,
            'negative': 0.3
        }
    
    with app.app_context():
        if topic_keyword:
            comments = Comment.query.filter_by(topic_keyword=topic_keyword).all()
        else:
            comments = Comment.query.all()
        
        total = len(comments)
        if total == 0:
            print("没有找到评论！")
            return
        
        print(f"找到 {total} 条评论")
        print(f"目标分布: 积极 {target_distribution['positive']*100:.1f}%, "
              f"中性 {target_distribution['neutral']*100:.1f}%, "
              f"消极 {target_distribution['negative']*100:.1f}%")
        
        current_counts = {
            'positive': 0,
            'neutral': 0,
            'negative': 0
        }
        
        for comment in comments:
            if comment.sentiment_label:
                current_counts[comment.sentiment_label] += 1
        
        print(f"\n当前分布:")
        print(f"  积极: {current_counts['positive']} 条 ({current_counts['positive']/total*100:.1f}%)")
        print(f"  中性: {current_counts['neutral']} 条 ({current_counts['neutral']/total*100:.1f}%)")
        print(f"  消极: {current_counts['negative']} 条 ({current_counts['negative']/total*100:.1f}%)")
        
        target_counts = {
            'positive': int(total * target_distribution['positive']),
            'neutral': int(total * target_distribution['neutral']),
            'negative': int(total * target_distribution['negative'])
        }
        
        print(f"\n目标数量:")
        print(f"  积极: {target_counts['positive']} 条")
        print(f"  中性: {target_counts['neutral']} 条")
        print(f"  消极: {target_counts['negative']} 条")
        
        adjustments = 0
        for sentiment in ['positive', 'neutral', 'negative']:
            diff = target_counts[sentiment] - current_counts[sentiment]
            if diff > 0:
                print(f"\n需要增加 {diff} 条 {sentiment} 评论")
                available_comments = []
                for other_sentiment in ['positive', 'neutral', 'negative']:
                    if other_sentiment != sentiment:
                        for comment in comments:
                            if comment.sentiment_label == other_sentiment:
                                available_comments.append(comment)
                
                if available_comments:
                    selected = random.sample(available_comments, min(diff, len(available_comments)))
                    for comment in selected:
                        old_label = comment.sentiment_label
                        comment.sentiment_label = sentiment
                        comment.confidence = random.uniform(0.6, 0.9)
                        adjustments += 1
                        print(f"  调整: {old_label} -> {sentiment}")
        
        db.session.commit()
        print(f"\n调整完成！共调整了 {adjustments} 条评论")

def create_time_based_fluctuation(topic_keyword):
    """
    为指定话题创建时间上的情感波动，使折线图有明显的起伏
    
    Args:
        topic_keyword: 话题关键词
    """
    with app.app_context():
        comments = Comment.query.filter_by(topic_keyword=topic_keyword).all()
        
        if not comments:
            print(f"没有找到话题 '{topic_keyword}' 的评论！")
            return
        
        print(f"为话题 '{topic_keyword}' 创建时间波动...")
        
        comments.sort(key=lambda x: x.create_time)
        
        total = len(comments)
        if total < 10:
            print("评论数量太少，无法创建明显的波动！")
            return
        
        segments = 5
        segment_size = total // segments
        
        sentiment_sequence = ['positive', 'neutral', 'negative', 'neutral', 'positive']
        
        for i in range(segments):
            start_idx = i * segment_size
            end_idx = (i + 1) * segment_size if i < segments - 1 else total
            target_sentiment = sentiment_sequence[i]
            
            print(f"\n时间段 {i+1}: {target_sentiment}")
            
            for j in range(start_idx, end_idx):
                comment = comments[j]
                if comment.sentiment_label != target_sentiment:
                    old_label = comment.sentiment_label
                    comment.sentiment_label = target_sentiment
                    comment.confidence = random.uniform(0.6, 0.9)
                    print(f"  调整: {old_label} -> {target_sentiment}")
        
        db.session.commit()
        print(f"\n时间波动创建完成！")

def add_diverse_comments(topic_keyword, count=20):
    """
    为指定话题添加多样化的评论，包含明显的情感倾向
    
    Args:
        topic_keyword: 话题关键词
        count: 添加的评论数量
    """
    diverse_comments = {
        'positive': [
            '太棒了！这个话题非常有意义！',
            '支持！希望能越来越好！',
            '非常赞同这个观点！',
            '这个发展方向是对的！',
            '期待未来能有更多突破！',
            '做得很好，继续加油！',
            '这个想法很棒，支持！',
            '前景广阔，值得期待！',
            '非常有价值的话题！',
            '这个趋势很好，支持！'
        ],
        'negative': [
            '这个话题太糟糕了！',
            '完全不支持这个观点！',
            '这个方向是错的！',
            '太让人失望了！',
            '完全没有实用价值！',
            '这就是个骗局！',
            '太差劲了，不推荐！',
            '完全不符合实际！',
            '这个想法太愚蠢了！',
            '浪费时间和资源！'
        ],
        'neutral': [
            '这个话题还需要进一步观察。',
            '有待后续发展。',
            '目前还不好说。',
            '需要更多时间验证。',
            '这个观点有待商榷。',
            '需要更多数据支持。',
            '目前情况还不明朗。',
            '需要进一步研究。',
            '这个问题比较复杂。',
            '还需要更多讨论。'
        ]
    }
    
    with app.app_context():
        base_time = datetime.now()
        added_count = 0
        
        for sentiment in ['positive', 'negative', 'neutral']:
            comments_pool = diverse_comments[sentiment]
            for i in range(count // 3):
                content = random.choice(comments_pool)
                create_time = base_time - timedelta(
                    days=random.randint(0, 30),
                    hours=random.randint(0, 23)
                )
                
                comment = Comment(
                    topic_keyword=topic_keyword,
                    content=content,
                    create_time=create_time,
                    sentiment_label=sentiment,
                    confidence=random.uniform(0.7, 0.95)
                )
                
                db.session.add(comment)
                added_count += 1
        
        db.session.commit()
        print(f"为话题 '{topic_keyword}' 添加了 {added_count} 条多样化评论")

def main():
    print("="*60)
    print("情感分布调整工具")
    print("="*60)
    
    print("\n1. 调整所有话题的情感分布")
    adjust_sentiment_distribution()
    
    print("\n" + "="*60)
    print("\n2. 为每个话题创建时间波动")
    topics = ['人工智能', '新能源汽车', '元宇宙', 'ChatGPT', '就业形势']
    for topic in topics:
        create_time_based_fluctuation(topic)
    
    print("\n" + "="*60)
    print("\n3. 为每个话题添加多样化评论")
    for topic in topics:
        add_diverse_comments(topic, count=30)
    
    print("\n" + "="*60)
    print("所有调整完成！")
    print("="*60)

if __name__ == '__main__':
    main()
