import sqlite3
from typing import List, Optional, Tuple, Iterator
from ..entity.comment import Comment


class CommentRepository:
    def __init__(self, db_name):
        self.db_name = db_name

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_name)

    def add_comment(self, comment: Comment, overwrite: bool = False) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM comment WHERE rpid = ?", (comment.rpid,))
            exists = cursor.fetchone()

            if exists:
                if overwrite:
                    update_sql = """
                    UPDATE comment SET
                        parentid = ?, rootid = ?, mid = ?, name = ?, level = ?, sex = ?,
                        information = ?, time = ?, single_reply_num = ?,
                        single_like_num = ?, sign = ?, ip_location = ?,
                        vip = ?, face = ?, oid = ?, type = ?
                    WHERE rpid = ?
                    """
                    params = (
                        comment.parentid,
                        comment.rootid,
                        comment.mid,
                        comment.name,
                        comment.level,
                        comment.sex,
                        comment.information,
                        comment.time,
                        comment.single_reply_num,
                        comment.single_like_num,
                        comment.sign,
                        comment.ip_location,
                        comment.vip,
                        comment.face,
                        comment.oid,
                        comment.rpid,
                        comment.type,
                    )
                    cursor.execute(update_sql, params)
                    conn.commit()
                    return True
                else:
                    return False
            else:
                insert_sql = """
                INSERT INTO comment (
                    rpid, parentid, rootid, mid, name, level, sex, information,
                    time, single_reply_num, single_like_num, sign,
                    ip_location, vip, face, oid, type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(insert_sql, comment.to_tuple())
                conn.commit()
                return True
        except sqlite3.Error as e:
            conn.rollback()
            print(f"添加/更新评论失败: {e}")
            return False
        finally:
            conn.close()

    def add_mini_comment(self, comment: Comment, overwrite: bool = False) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM comment WHERE rpid = ?", (comment.rpid,))
            exists = cursor.fetchone()

            if exists:
                if overwrite:
                    update_sql = """
                    UPDATE comment SET
                        parentid = ?, rootid=?, mid = ?,information = ?, time = ?, oid = ?, type = ?
                    WHERE rpid = ?
                    """
                    params = (
                        comment.parentid,
                        comment.rootid,
                        comment.mid,
                        comment.information,
                        comment.time,
                        comment.oid,
                        comment.rpid,
                        comment.type,
                    )
                    cursor.execute(update_sql, params)
                    conn.commit()
                    return True
                else:
                    return False
            else:
                insert_sql = """
                INSERT INTO comment (
                    rpid, parentid, rootid, mid, information, time, oid, type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """

                params_for_insert = (
                    comment.rpid,
                    comment.parentid,
                    comment.rootid,
                    comment.mid,
                    comment.information,
                    comment.time,
                    comment.oid,
                    comment.type,
                )
                cursor.execute(insert_sql, params_for_insert)
                conn.commit()
                return True
        except sqlite3.Error as e:
            conn.rollback()
            print(f"添加/更新评论失败: {e}")
            return False
        finally:
            conn.close()

    def delete_comments_by_mids(self, mids: List[int]) -> int:
        """
        根据一个或多个用户ID (mid) 删除评论。
        返回删除的记录数。
        """
        if not mids:
            return 0
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            placeholders = ",".join(["?"] * len(mids))
            delete_sql = f"DELETE FROM comment WHERE mid IN ({placeholders})"
            cursor.execute(delete_sql, tuple(mids))
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
        except sqlite3.Error as e:
            conn.rollback()
            print(f"按 mid 删除评论失败: {e}")
            return 0
        finally:
            conn.close()

    def delete_comments_by_oids(self, oids: List[int]) -> int:
        """
        根据一个或多个视频ID (oid) 删除评论。
        返回删除的记录数。
        """
        if not oids:
            return 0
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            placeholders = ",".join(["?"] * len(oids))
            delete_sql = f"DELETE FROM comment WHERE oid IN ({placeholders})"
            cursor.execute(delete_sql, tuple(oids))
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
        except sqlite3.Error as e:
            conn.rollback()
            print(f"按 oid 删除评论失败: {e}")
            return 0
        finally:
            conn.close()

    def get_comments_by_mid_paginated(
        self, mids: List[int], page: int = 1, page_size: int = 20
    ) -> List[Comment]:
        """
        根据一个或多个用户ID (mid) 查询评论，并支持分页。
        返回 Comment 对象的列表。
        """
        if not mids:
            return []
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20

        offset = (page - 1) * page_size
        conn = self._get_connection()
        cursor = conn.cursor()
        comments = []
        try:
            placeholders = ",".join(["?"] * len(mids))
            query_sql = f"""
            SELECT * FROM comment
            WHERE mid IN ({placeholders})
            ORDER BY time DESC -- 通常按时间倒序排列
            LIMIT ? OFFSET ?
            """
            cursor.execute(query_sql, tuple(mids + [page_size, offset]))
            for row in cursor.fetchall():
                comments.append(Comment.from_db_row(row))
        except sqlite3.Error as e:
            print(f"按 mid 分页查询评论失败: {e}")
        finally:
            conn.close()
        return comments

    def get_comments_by_oid_paginated(
        self, oids: List[int], page: int = 1, page_size: int = 20
    ) -> List[Comment]:
        """
        根据一个或多个视频ID (oid) 查询评论，并支持分页。
        返回 Comment 对象的列表。
        """
        if not oids:
            return []
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20

        offset = (page - 1) * page_size
        conn = self._get_connection()
        cursor = conn.cursor()
        comments = []
        try:
            placeholders = ",".join(["?"] * len(oids))
            query_sql = f"""
            SELECT * FROM comment
            WHERE oid IN ({placeholders})
            ORDER BY time DESC
            LIMIT ? OFFSET ?
            """
            cursor.execute(query_sql, tuple(oids + [page_size, offset]))
            for row in cursor.fetchall():
                comments.append(Comment.from_db_row(row))
        except sqlite3.Error as e:
            print(f"按 oid 分页查询评论失败: {e}")
        finally:
            conn.close()
        return comments

    def get_comments_by_mid_stream(self, mids: List[int]) -> Iterator[Comment]:
        if not mids:
            return

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(mids))
            query_sql = f"""
            SELECT * FROM comment
            WHERE mid IN ({placeholders})
            ORDER BY time ASC -- 流式通常按时间升序处理
            """
            cursor.execute(query_sql, tuple(mids))
            while True:
                rows = cursor.fetchmany(1000)
                if not rows:
                    break
                for row in rows:
                    yield Comment.from_db_row(row)
        except sqlite3.Error as e:
            print(f"按 mid 流式查询评论失败: {e}")
        finally:
            if conn:
                conn.close()

    def get_comments_by_oid_stream(self, oids: List[int]) -> Iterator[Comment]:
        """
        根据一个或多个视频ID (oid) 流式查询评论。
        返回一个 Comment 对象的迭代器。
        """
        if not oids:
            return

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(oids))
            query_sql = f"""
            SELECT * FROM comment
            WHERE oid IN ({placeholders})
            AND type = 1
            ORDER BY time ASC -- 流式通常按时间升序处理
            """
            cursor.execute(query_sql, tuple(oids))
            while True:
                rows = cursor.fetchmany(1000)
                if not rows:
                    break
                for row in rows:
                    yield Comment.from_db_row(row)
        except sqlite3.Error as e:
            print(f"按 oid 流式查询评论失败: {e}")
        finally:
            if conn:
                conn.close()

    def get_latest_comment_by_mid(self, mid: int) -> Optional[Comment]:
        if not mid:
            return None
        conn = self._get_connection()
        try:

            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query_sql = """
            SELECT rpid, oid, type FROM comment
            WHERE mid = ?
            ORDER BY time DESC
            LIMIT 1
            """
            cursor.execute(query_sql, (mid,))
            row = cursor.fetchone()
            if row:
                result_dict = {
                    "rpid": row["rpid"],
                    "oid": row["oid"],
                    "type": row["type"],
                }
                return result_dict
            return None
        except sqlite3.Error as e:
            print(f"获取用户最新评论失败: {e}")
            return None
        finally:
            if conn:
                conn.close()
