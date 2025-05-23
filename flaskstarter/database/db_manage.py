import sqlite3

from ..tools.config import BILI_DB_PATH


def init_bilibili_db(db_name):
    conn = None
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # 创建 user 表
        create_user_table_sql = """
        CREATE TABLE IF NOT EXISTS user (
            mid INTEGER PRIMARY KEY,  -- 用户ID，唯一标识，主键
            face TEXT,                -- 用户头像URL
            fans INTEGER,             -- 粉丝数
            friend INTEGER,           -- 关注数
            name TEXT,                -- 用户昵称
            sex TEXT,                 -- 性别
            sign TEXT,                -- 个性签名
            like_num INTEGER,         -- 获赞数
            vip INTEGER               -- VIP状态 (0: 非VIP, 1: VIP)
        );
        """
        cursor.execute(create_user_table_sql)
        print("表 'user' 创建成功或已存在。")

        # 创建 comment 表
        create_comment_table_sql = """
        CREATE TABLE IF NOT EXISTS comment (
            rpid INTEGER PRIMARY KEY,           -- 评论ID，唯一标识，主键
            parentid INTEGER,                   -- 父评论ID
            rootid INTEGER,                     -- root评论ID
            mid INTEGER,                        -- 发布评论的用户ID
            name TEXT,                          -- 发布评论的用户昵称
            level INTEGER,                      -- 用户等级
            sex TEXT,                           -- 用户性别
            information TEXT,                   -- 评论内容
            time INTEGER,                       -- 评论发布时间戳
            single_reply_num INTEGER,           -- 单条评论的回复数
            single_like_num INTEGER,            -- 单条评论的点赞数
            sign TEXT,                          -- 评论者个性签名 (可能与user表重复，但为了评论快照完整性保留)
            ip_location TEXT,                   -- IP归属地
            vip INTEGER,                        -- 评论者VIP状态 (0: 非VIP, 1: VIP)
            face TEXT,                          -- 评论者头像URL (可能与user表重复，但为了评论快照完整性保留)
            oid INTEGER,                        -- 视频或内容的ID (AV号或BV号对应的整数ID)
            type INTEGER            
        );
        """
        cursor.execute(create_comment_table_sql)
        print("表 'comment' 创建成功或已存在。")

        # 创建 bv 表
        create_bv_table_sql = """
        CREATE TABLE IF NOT EXISTS bv (
            oid INTEGER PRIMARY KEY,  -- 视频ID，唯一标识，主键
            bid TEXT,                  -- BV号
            title TEXT                -- 视频标题
        );
        """
        cursor.execute(create_bv_table_sql)
        print("表 'bv' 创建成功或已存在。")

        conn.commit()
        print(f"数据库 '{db_name}' 初始化完成。")

    except sqlite3.Error as e:
        print(f"数据库初始化失败: {e}")
    finally:
        if conn:
            conn.close()
if __name__ == "__main__":
    init_bilibili_db(BILI_DB_PATH)
