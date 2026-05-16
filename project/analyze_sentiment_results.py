import logging
from models import db, Comment
from db_init import app
from sqlalchemy import func, case

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def analyze_sentiment_distribution():
    """分析情感分布"""
    logger.info("="*60)
    logger.info("情感分析结果统计")
    logger.info("="*60)
    
    with app.app_context():
        total = Comment.query.count()
        positive = Comment.query.filter_by(sentiment_label='积极').count()
        negative = Comment.query.filter_by(sentiment_label='消极').count()
        neutral = Comment.query.filter_by(sentiment_label='中性').count()
        unlabeled = Comment.query.filter(
            (Comment.sentiment_label == None) | (Comment.sentiment_label == '')
        ).count()
        
        logger.info(f"总评论数: {total}")
        logger.info(f"积极: {positive} ({positive/total*100:.2f}%)")
        logger.info(f"消极: {negative} ({negative/total*100:.2f}%)")
        logger.info(f"中性: {neutral} ({neutral/total*100:.2f}%)")
        logger.info(f"未标注: {unlabeled}")
        logger.info("")
        
        logger.info("="*60)
        logger.info("各话题的情感分布")
        logger.info("="*60)
        
        topics = db.session.query(
            Comment.topic_keyword,
            func.count(Comment.id).label('total'),
            func.sum(case((Comment.sentiment_label == '积极', 1), else_=0)).label('positive'),
            func.sum(case((Comment.sentiment_label == '消极', 1), else_=0)).label('negative'),
            func.sum(case((Comment.sentiment_label == '中性', 1), else_=0)).label('neutral')
        ).group_by(Comment.topic_keyword).all()
        
        for topic in topics:
            topic_name = topic[0]
            total_count = topic[1]
            pos_count = topic[2] or 0
            neg_count = topic[3] or 0
            neu_count = topic[4] or 0
            
            logger.info(f"\n话题: {topic_name}")
            logger.info(f"  总数: {total_count}")
            logger.info(f"  积极: {pos_count} ({pos_count/total_count*100:.1f}%)")
            logger.info(f"  消极: {neg_count} ({neg_count/total_count*100:.1f}%)")
            logger.info(f"  中性: {neu_count} ({neu_count/total_count*100:.1f}%)")
        
        logger.info("")
        logger.info("="*60)
        logger.info("置信度统计")
        logger.info("="*60)
        
        avg_confidence = db.session.query(
            func.avg(Comment.confidence)
        ).filter(Comment.confidence.isnot(None)).scalar()
        
        logger.info(f"平均置信度: {avg_confidence:.4f}")
        
        logger.info("")
        logger.info("="*60)
        logger.info("示例数据")
        logger.info("="*60)
        
        examples = Comment.query.filter(
            Comment.sentiment_label.isnot(None)
        ).order_by(Comment.confidence.desc()).limit(5).all()
        
        for i, comment in enumerate(examples, 1):
            logger.info(f"\n{i}. 话题: {comment.topic_keyword}")
            logger.info(f"   情感: {comment.sentiment_label}")
            logger.info(f"   置信度: {comment.confidence:.4f}")
            logger.info(f"   内容: {comment.content[:50]}...")

if __name__ == '__main__':
    analyze_sentiment_distribution()
