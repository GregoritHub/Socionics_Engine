"""Source card arrangement; no content, capacity, navigation or Crux mapping."""
from .contracts import CueDescriptor, Kind, Ref

ARCANA = ("Magician", "High Priestess", "Empress", "Emperor", "Hierophant",
          "Lovers", "Chariot", "Strength", "Hermit", "Wheel of Fortune",
          "Justice", "Hanged Man", "Death", "Temperance", "Devil", "Tower",
          "Star", "Moon", "Sun", "Judgement", "World")
MINOR = ("Cup", "Sword", "Coin", "Wand")
STANDARD = ("Heart", "Spade", "Diamond", "Club")
SUIT_READINGS = (("Cup", "Psychology", "Sympathy"),
    ("Sword", "Politics", "Honesty"), ("Coin", "Economy", "Practicality"),
    ("Wand", "Science", "Creativity"), ("Heart", "Families", "Rapport"),
    ("Spade", "Labors", "Wisdom"), ("Diamond", "Resources", "Wealth"),
    ("Club", "Institutions", "Knowledge"))


def fold(rank):
    if type(rank) is not int or rank < 1:
        raise ValueError("positive numbered rank required")
    return (rank - 1) % 9 + 1


def catalog():
    cards = [CueDescriptor(Ref(Kind.CUE, "arcana:0", 1), "Fool",
                           "major_arcana", None, 0, None, None)]
    for rank, name in enumerate(ARCANA, 1):
        layer = "Super-Ego" if rank <= 9 else "Ego" if rank <= 18 else "Identity"
        cards.append(CueDescriptor(Ref(Kind.CUE, f"arcana:{rank}", 1), name,
                     "major_arcana", None, rank, fold(rank), layer))
    for deck, suits, courts in (("minor", MINOR, ("Page", "Knight", "Queen", "King")),
                                ("standard", STANDARD, ("Jack", "Queen", "King"))):
        for suit in suits:
            for rank in range(1, 11 + len(courts)):
                title = "Ace" if rank == 1 else str(rank) if rank <= 10 else courts[rank - 11]
                cards.append(CueDescriptor(Ref(Kind.CUE, f"{deck}:{suit}:{rank}", 1),
                    f"{title} of {suit}", deck, suit, rank, fold(rank), None))
    return tuple(cards)


CARDS = catalog()


def card(key):
    for value in CARDS:
        if value.ref.key == key:
            return value
    raise ValueError("unknown source card")
