"""
models.py — Datamodell for rom-til-rom festgenerator
"""

SLOTS = 6


class Participant:
    def __init__(self, name: str, room: str):
        self.name = name
        self.room = room          # eget rom (som vert)
        self.host_slot: int | None = None   # tidspunkt der de er vert
        self.route: list = [None] * SLOTS   # rom per tidspunkt

    def to_dict(self) -> dict:
        return {
            "name":      self.name,
            "room":      self.room,
            "host_slot": self.host_slot,
            "route":     self.route,
        }

    @staticmethod
    def from_dict(d: dict) -> "Participant":
        p = Participant(d["name"], d["room"])
        p.host_slot = d["host_slot"]
        p.route = d["route"]
        return p

    def __repr__(self):
        return f"<Participant {self.name!r} rom={self.room!r} økt={self.host_slot}>"


def parse_participants_text(text: str) -> list[Participant]:
    """
    Les deltakere fra fritekst.
    Kver linje: 'Navn, Romnummer'
    Tomme linjer og feilformaterte linjer ignoreres.
    """
    participants = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            name, room = [s.strip() for s in line.split(",", 1)]
            participants.append(Participant(name, room))
        except ValueError:
            continue
    return participants


def build_frontend_state(participants: list[Participant], slots: int = SLOTS) -> dict:
    """
    Bygg den JSON-strukturen frontend forventer:
      - timeslots: per økt, per rom, hvem er gjester/vert
      - routes:    per deltaker, full rute
      - participants: rådata for lagring
    """
    timeslots = []
    for ts in range(slots):
        room_map: dict[str, list[Participant]] = {}
        for p in participants:
            rm = p.route[ts] or ""
            if rm:
                room_map.setdefault(rm, []).append(p)
        rooms = []
        for room, plist in sorted(room_map.items()):
            host = next(
                (p for p in plist if p.host_slot == ts and p.room == room), None
            )
            rooms.append({
                "room":   room,
                "host":   host.name if host else None,
                "guests": [p.name for p in plist if p != host],
                "count":  len(plist),
            })
        timeslots.append({"slot": ts + 1, "rooms": rooms})

    routes = [
        {
            "name":      p.name,
            "host_slot": p.host_slot,
            "route":     [r or "?" for r in p.route],
        }
        for p in participants
    ]

    return {
        "timeslots":    timeslots,
        "routes":       routes,
        "slots":        slots,
        "participants": [p.to_dict() for p in participants],
    }
