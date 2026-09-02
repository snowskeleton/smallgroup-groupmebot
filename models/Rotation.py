from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

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


def meeting_dates(start: datetime, through: datetime, weekday: int,
                  existing: Optional[Set[str]] = None) -> List[datetime]:
    """Every occurrence of `weekday` from `start` to `through` that's missing.

    Working from what's absent rather than from the last row means a one-off
    event dated months out — a retreat, a conference — doesn't stop the regular
    meetings in between from being generated.
    """
    cursor = start + timedelta(days=(weekday - start.weekday()) % 7)
    existing = existing or set()

    dates = []
    while cursor <= through:
        if cursor.strftime(DATE_FORMAT) not in existing:
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


def fill_times(dated: List[Tuple[int, Dict[str, str]]], default_time: str,
               weekday: int, today: datetime) -> List[Tuple[int, str, str]]:
    """Put the default time on any regular meeting that's missing one.

    Time is scaffolding rather than a commitment, so unlike the rotations it is
    filled as far out as dates go. Doing it here instead of only at row creation
    means a row created while Config was incomplete gets repaired on the next
    run rather than staying blank forever.

    Off-day rows are left alone: a Sunday picnic doesn't start at the regular
    Thursday time.
    """
    if not default_time:
        return []

    updates = []
    for row_number, record in dated:
        if str(record.get("Time", "")).strip():
            continue
        date = parse_date(record)
        if date is None or date < today or date.weekday() != weekday:
            continue
        record["Time"] = default_time
        updates.append((row_number, "Time", default_time))
    return updates


def assign_rows(headers: List[str], dated: List[Tuple[int, Dict[str, str]]],
                rotations: List[Rotation], roster, pools: Dict[str, List[str]],
                today: datetime, horizon: datetime,
                weekday: Optional[int] = None) -> List[Tuple[int, str, str]]:
    """Fill blank rotation cells on regular meetings inside the horizon.

    `dated` is (row number, record) in *date* order, not sheet order — a one-off
    event added out of band can sit physically below meetings that fall before
    it, and turn-taking has to follow the calendar rather than the row numbering.

    Rows that aren't on the regular meeting day are skipped. An extra Sunday
    event isn't part of the rotation, so nobody should spend their turn on it.
    Typing a name in yourself still works and still counts; the bot just won't
    volunteer anyone.

    Cells that already contain anything are left strictly alone.
    """
    entry_lists = {r.name: r.entries(roster, pools) for r in rotations}
    updates: List[Tuple[int, str, str]] = []
    history: List[Dict[str, str]] = []

    for row_number, record in dated:
        date = parse_date(record)
        if date is None:
            continue

        # Every dated row feeds the cursor, including past ones and off-day
        # ones a human filled in. Only *assignment* is restricted.
        history.append(record)

        if date < today or date > horizon:
            continue
        if weekday is not None and date.weekday() != weekday:
            continue

        for rotation in rotations:
            if rotation.column not in headers:
                continue
            if str(record.get(rotation.column, "")).strip():
                continue

            value = next_entry(rotation, history[:-1],
                               entry_lists.get(rotation.name, []))
            if not value:
                continue

            record[rotation.column] = value
            updates.append((row_number, rotation.column, value))

    return updates


def parse_date(record: Dict[str, str]) -> Optional[datetime]:
    try:
        return datetime.strptime(str(record.get("Date", "")).strip(), DATE_FORMAT)
    except ValueError:
        return None
