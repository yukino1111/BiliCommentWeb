class Comment:

    def __init__(
        self,
        rpid: int,
        parentid: int = None,
        rootid: int = None,
        mid: int = None,
        name: str = None,
        level: int = None,
        sex: str = None,
        information: str = None,
        time: int = None,
        single_reply_num: int = None,
        single_like_num: int = None,
        sign: str = None,
        ip_location: str = None,
        vip: int = None,
        face: str = None,
        oid: int = None,
        type: int = None,
    ):
        self.rpid = rpid
        self.parentid = parentid
        self.rootid = rootid
        self.mid = mid
        self.name = name
        self.level = level
        self.sex = sex
        self.information = information
        self.time = time
        self.single_reply_num = single_reply_num
        self.single_like_num = single_like_num
        self.sign = sign
        self.ip_location = ip_location
        self.vip = vip
        self.face = face
        self.oid = oid
        self.type = type

    def to_tuple(self):
        return (
            self.rpid,
            self.parentid,
            self.rootid,
            self.mid,
            self.name,
            self.level,
            self.sex,
            self.information,
            self.time,
            self.single_reply_num,
            self.single_like_num,
            self.sign,
            self.ip_location,
            self.vip,
            self.face,
            self.oid,
            self.type,
        )

    @classmethod
    def from_db_row(cls, row: tuple):
        if row is None:
            return None
        return cls(
            rpid=row[0],
            parentid=row[1],
            rootid=row[2],
            mid=row[3],
            name=row[4],
            level=row[5],
            sex=row[6],
            information=row[7],
            time=row[8],
            single_reply_num=row[9],
            single_like_num=row[10],
            sign=row[11],
            ip_location=row[12],
            vip=row[13],
            face=row[14],
            oid=row[15],
            type=row[16],
        )
