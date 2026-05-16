from db_init import app, db
from models import Comment
from sqlalchemy import text

def migrate_database():
    """
    迁移数据库，添加 manual_label 列
    """
    with app.app_context():
        try:
            db.session.execute(text('ALTER TABLE comments ADD COLUMN manual_label VARCHAR(20)'))
            db.session.commit()
            print("成功添加 manual_label 列")
        except Exception as e:
            db.session.rollback()
            if "duplicate column name" in str(e).lower():
                print("manual_label 列已存在，跳过迁移")
            else:
                print(f"迁移失败: {e}")

if __name__ == '__main__':
    migrate_database()
