import logging
from models import db, Comment
from db_init import app

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_database():
    """检查数据库中的数据"""
    logger.info("="*60)
    logger.info("检查数据库中的数据")
    logger.info("="*60)
    
    try:
        with app.app_context():
            # 查询所有评论
            all_comments = Comment.query.all()
            logger.info(f"数据库中总共有 {len(all_comments)} 条评论")
            
            # 按话题分组统计
            from sqlalchemy import func
            topic_stats = db.session.query(
                Comment.topic_keyword,
                func.count(Comment.id).label('count')
            ).group_by(Comment.topic_keyword).all()
            
            logger.info("\n按话题分组统计:")
            for topic, count in topic_stats:
                logger.info(f"  {topic}: {count} 条")
            
            # 查询最近的评论
            recent_comments = Comment.query.order_by(Comment.create_time.desc()).limit(5).all()
            logger.info("\n最近的 5 条评论:")
            for i, comment in enumerate(recent_comments, 1):
                logger.info(f"  {i}. [{comment.topic_keyword}] {comment.content[:50]}...")
            
            # 查询未分析的情感标签
            unlabeled_count = Comment.query.filter_by(sentiment_label=None).count()
            labeled_count = Comment.query.filter(Comment.sentiment_label != None).count()
            
            logger.info(f"\n情感标注情况:")
            logger.info(f"  已标注: {labeled_count} 条")
            logger.info(f"  未标注: {unlabeled_count} 条")
            
            logger.info("\n" + "="*60)
            logger.info("数据库检查完成")
            logger.info("="*60)
            
            return {
                'total': len(all_comments),
                'topic_stats': topic_stats,
                'recent_comments': recent_comments,
                'labeled_count': labeled_count,
                'unlabeled_count': unlabeled_count
            }
            
    except Exception as e:
        logger.error(f"检查数据库失败: {e}")
        logger.error(f"错误类型: {type(e).__name__}")
        return None

if __name__ == '__main__':
    result = check_database()
    
    if result:
        logger.info("\n✅ 数据库检查完成")
    else:
        logger.error("\n❌ 数据库检查失败")
