from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday"]

DATE_FORMAT = "%m/%d/%Y"


class Rotation:
    """One row of the Rotations tab.

    Pool is either 'People', 'Households', or the name of another tab holding a
    plain ordered list — that last option is how group-level rotations work
    without touching code.
    """

    def __init__(self, row: Dict[str, object]):
        self.name = str(row.get("Rotation", "")).strip()
        self.column = str(row.get("Column", "")).strip()
        self.pool = str(row.get("Pool", "")).strip()
        self.opt_in = str(row.get("Opt-in", "")).strip()

    def entries(self, roster, pools: Dict[str, List[str]]) -> List[str]:
        """The ordered candidate list this rotation cycles through."""
        pool = self.pool.lower()
        if pool == "people":
            return roster.active_people(self.opt_in)
        if pool == "households":
            return roster.active_households(self.opt_in)
        for tab, values in pools.items():
            if tab.strip().lower() == pool:
                return list(values)
        return []

    def __repr__(self) -> str:
        return f"<Rotation {self.name!r} column={self.column!r} pool={self.pool!r}>"


def next_entry(rotation: Rotation, history: List[Dict[str, str]],
               entries: List[str]) -> str:
    """Whose turn is it.

    There is no stored cursor. We scan the schedule upward for the most recent
    value that matches something in the pool, and take the next one down,
    wrapping at the bottom.

    Values that aren't in the pool are skipped rather than treated as a
    position. That is what makes an off-site week ("Panera") free: nobody loses
    their turn, because the rotation reads straight past it to the last real
    entry. It also means a human-entered substitute who isn't in the pool
    doesn't derail the sequence.
    """
    if not entries:
        return ""

    index = {value.strip().lower(): i for i, value in enumerate(entries)}

    for row in reversed(history):
        value = str(row.get(rotation.column, "")).strip().lower()
        if value in index:
            return entries[(index[value] + 1) % len(entries)]

    return entries[0]


def parse_weekday(name: str) -> int:
    """Monday=0 … Sunday=6, matching datetime.weekday()."""
    key = str(name).strip().lower()
    if key in WEEKDAYS:
        return WEEKDAYS.index(key)
    return 6  # Sunday


def meeting_dates(start_after: datetime, through: datetime, weekday: int) -> List[datetime]:
    """Every occurrence of `weekday` strictly after start_after, up to through."""
    cursor = start_after + timedelta(days=1)
    cursor += timedelta(days=(weekday - cursor.weekday()) % 7)

    dates = []
    while cursor <= through:
        dates.append(cursor)
        cursor += timedelta(days=7)
    return dates


def blank_rows(headers: List[str], dates: List[datetime],
               default_time: str) -> List[List[str]]:
    """Dated placeholder rows with nothing assigned yet.

    Dates and assignments have different useful horizons: you want months of
    dates to hang notes off, but a leader named in January for May is a
    commitment nobody made. So generation lays down bare dates, and assignment
    fills them in later, close to the day.
    """
    rows = []
    for date in dates:
        record = {h: "" for h in headers}
        record["Date"] = date.strftime(DATE_FORMAT)
        if "Time" in record:
            record["Time"] = default_time
        rows.append([record[h] for h in headers])
    return rows


def assign_rows(headers: List[str], records: List[Dict[str, str]],
                rotations: List[Rotation], roster, pools: Dict[str, List[str]],
                today: datetime, horizon: datetime) -> List[Tuple[int, str, str]]:
    """Fill blank rotation cells on rows falling inside the assignment horizon.

    Returns (record index, column, value) for each cell to write. Cells that
    already contain anything are left strictly alone — that is the whole safety
    guarantee, so it lives in the one `continue` below.

    Assigning late is also what lets a new person start leading soon after
    they're added, instead of waiting out a queue of pre-assigned months.
    """
    entry_lists = {r.name: r.entries(roster, pools) for r in rotations}
    updates: List[Tuple[int, str, str]] = []

    for index, record in enumerate(records):
        try:
            date = datetime.strptime(str(record.get("Date", "")).strip(), DATE_FORMAT)
        except ValueError:
            continue
        if date < today or date > horizon:
            continue

        for rotation in rotations:
            if rotation.column not in headers:
                continue
            if str(record.get(rotation.column, "")).strip():
                continue

            # Only rows *above* this one set the cursor, so an assignment made
            # further down the sheet can't reach back and reorder history.
            value = next_entry(rotation, records[:index],
                               entry_lists.get(rotation.name, []))
            if not value:
                continue

            record[rotation.column] = value
            updates.append((index, rotation.column, value))

    return updates


def last_scheduled_date(history: List[Dict[str, str]]) -> Optional[datetime]:
    latest = None
    for row in history:
        raw = str(row.get("Date", "")).strip()
        if not raw:
            continue
        try:
            parsed = datetime.strptime(raw, DATE_FORMAT)
        except ValueError:
            continue
        if latest is None or parsed > latest:
            latest = parsed
    return latest
