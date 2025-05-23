import sqlite3
from typing import List, Optional, Tuple
from ..entity.bv import Bv


class BvRepository:
    def __init__(self, db_name):
        self.db_name = db_name

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_name)

    def add_or_update_bv(self, bv: Bv) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            insert_or_replace_sql = """
            INSERT OR REPLACE INTO bv (
                oid, bid, title
            ) VALUES (?, ?, ?)
            """
            cursor.execute(insert_or_replace_sql, bv.to_tuple())
            conn.commit()
            return True
        except sqlite3.Error as e:
            conn.rollback()
            print(f"添加/更新失败: {e}")
            return False
        finally:
            conn.close()

    def delete_bvs_by_oids(self, oids: List[int]) -> int:
        if not oids:
            return 0
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            placeholders = ",".join(["?"] * len(oids))
            delete_sql = f"DELETE FROM bv WHERE oid IN ({placeholders})"
            cursor.execute(delete_sql, tuple(oids))
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
        except sqlite3.Error as e:
            conn.rollback()
            print(f"删除 bv 失败: {e}")
            return 0
        finally:
            conn.close()

    def get_information_by_oids(self, oids: List[int]) -> List[Bv]:
        if not oids:
            return []
        conn = self._get_connection()
        cursor = conn.cursor()
        bvs = []
        try:
            placeholders = ",".join(["?"] * len(oids))
            query_sql = f"SELECT * FROM bv WHERE oid IN ({placeholders})"
            cursor.execute(query_sql, tuple(oids))
            for row in cursor.fetchall():
                bvs.append(Bv.from_db_row(row))
        except sqlite3.Error as e:
            print(f"查询失败: {e}")
        finally:
            conn.close()
        return bvs

    def get_information_by_bids(self, bids: List[str]) -> List[Bv]:
        if not bids:
            return []
        conn = self._get_connection()
        cursor = conn.cursor()
        bvs = []
        try:
            placeholders = ",".join(["?"] * len(bids))
            query_sql = f"SELECT * FROM bv WHERE bid IN ({placeholders})"
            cursor.execute(query_sql, tuple(bids))
            for row in cursor.fetchall():
                bvs.append(Bv.from_db_row(row))
        except sqlite3.Error as e:
            print(f"查询失败: {e}")
        finally:
            conn.close()
        return bvs

    def get_oids_by_bids(self, bids: List[str]) -> List[int]:
        if not bids:
            return []
        conn = self._get_connection()
        cursor = conn.cursor()
        oids = []
        try:
            placeholders = ",".join(["?"] * len(bids))
            query_sql = f"SELECT oid FROM bv WHERE bid IN ({placeholders})"
            cursor.execute(query_sql, tuple(bids))
            for row in cursor.fetchall():
                oids.append(row[0])
        except sqlite3.Error as e:
            print(f"查询失败: {e}")
        finally:
            conn.close()
        return oids

    def get_bids_by_oids(self, oids: List[int]) -> List[str]:
        if not oids:
            return []
        conn = self._get_connection()
        cursor = conn.cursor()
        bids = []
        try:
            placeholders = ",".join(["?"] * len(oids))
            query_sql = f"SELECT bid FROM bv WHERE oid IN ({placeholders})"
            cursor.execute(query_sql, tuple(oids))
            for row in cursor.fetchall():
                bids.append(row[1])
        except sqlite3.Error as e:
            print(f"查询失败: {e}")
        finally:
            conn.close()
        return bids
