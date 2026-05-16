import logging
from models import db, Comment
from db_init import app
from sqlalchemy import inspect

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_table_structure():
    """检查数据库表结构"""
    logger.info("="*60)
    logger.info("检查数据库表结构")
    logger.info("="*60)
    
    try:
        with app.app_context():
            # 获取表结构
            inspector = inspect(db.engine)
            columns = inspector.get_columns('comments')
            
            logger.info(f"comments 表共有 {len(columns)} 个字段:")
            logger.info("")
            
            for column in columns:
                logger.info(f"  字段名: {column['name']}")
                logger.info(f"    类型: {column['type']}")
                logger.info(f"    可为空: {column['nullable']}")
                logger.info(f"    默认值: {column.get('default', '无')}")
                logger.info("")
            
            # 检查是否有 sentiment_label 和 confidence 字段
            column_names = [col['name'] for col in columns]
            
            logger.info("="*60)
            logger.info("字段检查结果:")
            logger.info("="*60)
            
            if 'sentiment_label' in column_names:
                logger.info("✅ sentiment_label 字段已存在")
            else:
                logger.error("❌ sentiment_label 字段不存在")
            
            if 'confidence' in column_names:
                logger.info("✅ confidence 字段已存在")
            else:
                logger.error("❌ confidence 字段不存在")
            
            logger.info("")
            
            # 检查数据
            logger.info("="*60)
            logger.info("数据统计:")
            logger.info("="*60)
            
            total_comments = Comment.query.count()
            labeled_comments = Comment.query.filter(Comment.sentiment_label.isnot(None)).count()
            unlabeled_comments = Comment.query.filter(Comment.sentiment_label.is_(None)).count()
            
            logger.info(f"总评论数: {total_comments}")
            logger.info(f"已标注情感: {labeled_comments}")
            logger.info(f"未标注情感: {unlabeled_comments}")
            
            # 检查 confidence 字段的数据
            if 'confidence' in column_names:
                comments_with_confidence = Comment.query.filter(Comment.confidence.isnot(None)).count()
                logger.info(f"有置信度的评论: {comments_with_confidence}")
            
            logger.info("")
            logger.info("="*60)
            logger.info("检查完成")
            logger.info("="*60)
            
            return {
                'columns': columns,
                'has_sentiment_label': 'sentiment_label' in column_names,
                'has_confidence': 'confidence' in column_names,
                'total_comments': total_comments,
                'labeled_comments': labeled_comments,
                'unlabeled_comments': unlabeled_comments
            }
            
    except Exception as e:
        logger.error(f"检查表结构失败: {e}")
        logger.error(f"错误类型: {type(e).__name__}")
        return None

if __name__ == '__main__':
    result = check_table_structure()
    
    if result:
        if result['has_sentiment_label'] and result['has_confidence']:
            logger.info("\n✅ 表结构检查完成，所有必需字段都存在！")
        else:
            logger.error("\n❌ 表结构缺少必需字段，需要迁移！")
    else:
        logger.error("\n❌ 表结构检查失败")
