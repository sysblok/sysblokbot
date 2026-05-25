TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


class TrelloBoard:
    def __init__(self):
        self.id = None
        self.name = None
        self.url = None
        self._ok = True

    def __bool__(self):
        return self._ok

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Board<id={self.id}, name={self.name}, url={self.url}>"

    def to_dict(self):
        return {"id": self.id, "name": self.name, "url": self.url}


class TrelloList:
    def __init__(self):
        self.id = None
        self.name = None
        self.board_id = None
        self._ok = True

    def __bool__(self):
        return self._ok

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"List<id={self.id}, name={self.name}>"

    def to_dict(self):
        return {"id": self.id, "name": self.name, "board_id": self.board_id}


class TrelloCardLabel:
    def __init__(self):
        self.id = None
        self.name = None
        self.color = None
        self._ok = True

    def __bool__(self):
        return self._ok

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"CardLabel<name={self.name}, color={self.color}>"


class TrelloCard:
    def __init__(self):
        self.id = None
        self.name = None
        self.labels = []
        self.url = None
        self.due = None
        self.lst = None
        self.members = []
        self._ok = True

    def __bool__(self):
        return self._ok

    def __str__(self):
        return self.url

    def __repr__(self):
        return f"Card<id={self.id}, name={self.name}, url={self.url} members={self.members}>"

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(self.id)


class TrelloMember:
    def __init__(self):
        self.id = None
        self.username = None
        self.full_name = None

    def __str__(self):
        return self.username

    def __repr__(self):
        return f"Member<id={self.id}, name={self.username}, full name={self.full_name}>"

    def __eq__(self, other):
        return isinstance(other, TrelloMember) and self.username == other.username

    def __lt__(self, other):
        return isinstance(other, TrelloMember) and self.username < other.username

    def __hash__(self):
        return hash(self.username)


class CardCustomFields:
    def __init__(self, card_id):
        self.card_id = card_id
        self.authors = None
        self.editors = None
        self.illustrators = None
        self.cover = None
        self.title = None
        self.google_doc = None

    def __repr__(self):
        return f"CardCustomFields<id={self.card_id}, title={self.title}>"
