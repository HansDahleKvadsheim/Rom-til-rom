"""
scheduler.py — Planleggingslogikk for rom-til-rom festgenerator

Funksjoner:
  assign_host_groups   Tilfeldig fordeling av verter per økt
  assign_routes        Beregn ruter for alle deltakere
  update_timeslot      Rekalkuler én økt etter endringer
  flytt_rom            Flytt et rom til annet tidspunkt (uten gjester)
  bytt_rom             Bytt to rom mellom sine tidspunkt (beholder gjester)
  bytt_deltakere       Bytt to gjester i en økt
  flytt_deltaker       Flytt én gjest til annet rom i samme økt
  fjern_deltaker       Fjern en deltaker og redistribuer
"""

import random
from models import Participant, SLOTS


def assign_host_groups(participants: list[Participant], slots: int = SLOTS) -> None:
    """Bland tilfeldig og del inn i like store vertegrupper per økt."""
    random.shuffle(participants)
    n = len(participants)
    base, extra = divmod(n, slots)
    idx = 0
    for i in range(slots):
        size = base + (1 if i < extra else 0)
        for p in participants[idx : idx + size]:
            p.host_slot = i
        idx += size


def assign_routes(participants: list[Participant], slots: int = SLOTS) -> None:
    """
    For hver økt: verter blir i sitt rom, gjester fordeles round-robin
    tilfeldig mellom rommene som er åpne den økten.
    """
    for ts in range(slots):
        hosts = [p for p in participants if p.host_slot == ts]
        if not hosts:
            raise ValueError(f"Tidspunkt {ts + 1} har ingen verter!")
        non_hosts = [p for p in participants if p.host_slot != ts]
        random.shuffle(non_hosts)
        for i, p in enumerate(non_hosts):
            p.route[ts] = hosts[i % len(hosts)].room
        for p in hosts:
            p.route[ts] = p.room


def update_timeslot(
    ts: int,
    participants: list[Participant],
    exclude_room: str | None = None,
) -> None:
    """
    Rekalkuler gjeste-tilordninger for én økt.
    Brukes etter at et rom er fjernet eller vert er byttet.
    exclude_room: hopp over dette rommet ved round-robin.
    """
    hosts = [
        p for p in participants
        if p.host_slot == ts and (exclude_room is None or p.room != exclude_room)
    ]
    if not hosts:
        for p in participants:
            p.route[ts] = ""
        return
    non_hosts = [p for p in participants if p.host_slot != ts]
    random.shuffle(non_hosts)
    for i, p in enumerate(non_hosts):
        p.route[ts] = hosts[i % len(hosts)].room
    for p in participants:
        if p.host_slot == ts:
            p.route[ts] = p.room


def flytt_rom(room: str, target_slot: int, participants: list[Participant]) -> None:
    """
    Flytt et rom (uten gjester) til et annet tidspunkt.
    Gjestene som var i rommet i kildeøkten redistribueres.
    """
    mover = next((p for p in participants if p.room == room), None)
    if not mover:
        raise ValueError(f"Ingen deltaker med rom '{room}'.")
    source_slot = mover.host_slot
    if source_slot == target_slot:
        raise ValueError("Rommet er allerede i dette tidspunktet.")
    other_hosts = [
        p for p in participants
        if p.host_slot == source_slot and p.room != room
    ]
    if not other_hosts:
        raise ValueError(
            f"Kan ikke flytte: økt {source_slot + 1} ville stå uten verter."
        )
    idx = 0
    for p in participants:
        if p.route[source_slot] == room:
            p.route[source_slot] = other_hosts[idx % len(other_hosts)].room
            idx += 1
    mover.host_slot = target_slot
    mover.route[target_slot] = mover.room


def bytt_rom(room1: str, room2: str, participants: list[Participant]) -> None:
    """
    Bytt to rom mellom sine tidspunkter.
    Deltakere som var tilordnet hvert rom følger med så langt det lar seg gjøre
    (minimal endring: bare de to kolonnene oppdateres).
    Fungerer både for rom i samme økt og på tvers av økter.
    """
    p1 = next((p for p in participants if p.room == room1), None)
    p2 = next((p for p in participants if p.room == room2), None)
    if not p1 or not p2:
        raise ValueError("Ett eller begge rom ble ikke funnet.")
    ts1, ts2 = p1.host_slot, p2.host_slot

    # Lagre kryssede ruter før vi endrer noe
    cross1 = p1.route[ts2]   # hva p1 hadde i p2s økt
    cross2 = p2.route[ts1]   # hva p2 hadde i p1s økt

    # Oppdater alle som pekte på room1 i ts1 → pek på room2
    for p in participants:
        if p.route[ts1] == room1:
            p.route[ts1] = room2
    # Oppdater alle som pekte på room2 i ts2 → pek på room1
    for p in participants:
        if p.route[ts2] == room2:
            p.route[ts2] = room1

    # Bytt host_slot
    p1.host_slot, p2.host_slot = ts2, ts1
    p1.route[ts2] = p1.room
    p2.route[ts1] = p2.room

    # Rydd opp kryss-ruter
    if cross2 != p1.room:
        p1.route[ts1] = cross2
    if cross1 != p2.room:
        p2.route[ts2] = cross1


def bytt_deltakere(
    ts: int, name1: str, name2: str, participants: list[Participant]
) -> None:
    """
    Bytt romtilordning for to gjester i én økt.
    Verter kan ikke byttes (de er alltid i sitt eget rom).
    """
    p1 = next((p for p in participants if p.name == name1), None)
    p2 = next((p for p in participants if p.name == name2), None)
    if not p1 or not p2:
        raise ValueError("En eller begge deltakere ble ikke funnet.")
    if p1.host_slot == ts or p2.host_slot == ts:
        raise ValueError(
            "Kan ikke bytte: en av deltakerne er vert i denne økten."
        )
    p1.route[ts], p2.route[ts] = p2.route[ts], p1.route[ts]


def flytt_deltaker(
    ts: int, name: str, target_room: str, participants: list[Participant]
) -> None:
    """
    Flytt én gjest til et annet åpent rom i samme økt.
    """
    p = next((p for p in participants if p.name == name), None)
    if not p:
        raise ValueError("Deltakeren ble ikke funnet.")
    if p.host_slot == ts:
        raise ValueError("Verter kan ikke flyttes.")
    open_rooms = [q.room for q in participants if q.host_slot == ts]
    if target_room not in open_rooms:
        raise ValueError(f"Rom '{target_room}' er ikke åpent i økt {ts + 1}.")
    p.route[ts] = target_room


def endre_deltaker(
    old_name: str, new_name: str, new_room: str, participants: list[Participant]
) -> None:
    """
    Endre navn og/eller romnummer for en eksisterende deltaker.
    Oppdaterer alle rute-referanser til det gamle rommet.
    """
    p = next((q for q in participants if q.name == old_name), None)
    if not p:
        raise ValueError(f"Deltaker '{old_name}' ikke funnet.")
    if new_name != old_name and any(q.name == new_name for q in participants):
        raise ValueError(f"Navn '{new_name}' er allerede i bruk.")
    if new_room != p.room and any(q.room == new_room for q in participants if q.name != old_name):
        raise ValueError(f"Rom '{new_room}' er allerede i bruk.")

    if new_room != p.room:
        old_room = p.room
        for q in participants:
            q.route = [new_room if r == old_room else r for r in q.route]
        p.room = new_room

    p.name = new_name


def legg_til_deltaker(name: str, room: str, participants: list[Participant]) -> None:
    """
    Legg til en ny deltaker i en eksisterende timeplan.
    Tildeler verteøkt med færrest verter, og plasserer deltakeren i det
    minst besøkte rommet i hver av de andre øktene.
    Verteøkten rekalkuleres slik at det nye rommet inkluderes.
    """
    if any(p.name == name for p in participants):
        raise ValueError(f"Deltaker '{name}' finnes allerede.")
    if any(p.room == room for p in participants):
        raise ValueError(f"Rom '{room}' er allerede i bruk.")

    new_p = Participant(name, room)

    host_counts = [sum(1 for p in participants if p.host_slot == ts) for ts in range(SLOTS)]
    best_slot = host_counts.index(min(host_counts))
    new_p.host_slot = best_slot
    new_p.route[best_slot] = room

    for ts in range(SLOTS):
        if ts == best_slot:
            continue
        hosts_in_slot = [p for p in participants if p.host_slot == ts]
        if not hosts_in_slot:
            new_p.route[ts] = ""
            continue
        visit_counts = {
            h.room: sum(1 for p in participants if p.route[ts] == h.room)
            for h in hosts_in_slot
        }
        new_p.route[ts] = min(visit_counts, key=visit_counts.get)

    participants.append(new_p)
    update_timeslot(best_slot, participants)


def fjern_deltaker(name: str, participants: list[Participant]) -> None:
    """
    Fjern en deltaker og redistribuer gjestene i dens verteøkt.
    Muterer lista in-place.
    """
    removed = next((p for p in participants if p.name == name), None)
    if not removed:
        raise ValueError("Deltakeren ble ikke funnet.")
    ts = removed.host_slot
    participants.remove(removed)
    try:
        update_timeslot(ts, participants)
    except ValueError:
        for p in participants:
            p.route[ts] = ""
