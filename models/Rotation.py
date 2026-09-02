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
    """Whose turn is it: whoever has gone longest without one.

    There is no stored cursor. We read the schedule above this row, note when
    each pool member last came up, and pick the one who has waited longest.
    Anyone who has never come up sorts first; ties break on order in the sheet,
    so a rotation with no history yet runs straight down the People tab.

    With nobody swapped this is identical to walking the list in order — the
    person who last went is by definition the least recently used. Where it
    differs is when a human edits the schedule.

    Say the pool is Jessica, Levi, Sara, Christine, and Jessica covers for
    Christine in week 4. Taking "the next one after the most recent" would read
    Jessica in week 4 and hand week 5 to Levi, which quietly costs Christine
    her turn — she'd wait until week 7, and end a cycle short. Here Christine
    still hasn't had a turn, so she simply goes next.

    The same property makes a newly added person start soon rather than waiting
    out the existing queue, and makes an off-site week free: a Location like
    "Panera" belongs to no pool member, so it updates nobody's last-served
    position and the rotation carries on as though that week hadn't happened.
    """
    if not entries:
        return ""

    order = {entry.strip().lower(): i for i, entry in enumerate(entries)}
    last_served: Dict[str, int] = {}
    for position, row in enumerate(history):
        value = str(row.get(rotation.column, "")).strip().lower()
        if value:
            last_served[value] = position

    def staleness(entry: str):
        key = entry.strip().lower()
        # -1 for never served, so they come before anyone with a real turn.
        return (last_served.get(key, -1), order[key])

    return min(entries, key=staleness)


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
