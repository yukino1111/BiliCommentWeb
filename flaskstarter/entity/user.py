class User:

    def __init__(
        self,
        mid: int,
        face: str = None,
        fans: int = None,
        friend: int = None,
        name: str = None,
        sex: str = None,
        sign: str = None,
        like_num: int = None,
        vip: int = None,
    ):
        self.mid = mid
        self.face = face
        self.fans = fans
        self.friend = friend
        self.name = name
        self.sex = sex
        self.sign = sign
        self.like_num = like_num
        self.vip = vip

    def to_tuple(self):
        return (
            self.mid,
            self.face,
            self.fans,
            self.friend,
            self.name,
            self.sex,
            self.sign,
            self.like_num,
            self.vip,
        )

    @classmethod
    def from_db_row(cls, row: tuple):
        if row is None:
            return None
        return cls(
            mid=row[0],
            face=row[1],
            fans=row[2],
            friend=row[3],
            name=row[4],
            sex=row[5],
            sign=row[6],
            like_num=row[7],
            vip=row[8],
        )
