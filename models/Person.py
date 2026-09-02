from typing import Dict, List


TRUTHY = {"TRUE", "YES", "Y", "X", "1", "✓"}


def truthy(value) -> bool:
    """Sheets checkboxes arrive as bools or as the strings TRUE/FALSE."""
    if isinstance(value, bool):
        return value
    return str(value).strip().upper() in TRUTHY


class Person:
    """One row of the People tab."""

    def __init__(self, row: Dict[str, object]):
        self.name = str(row.get("Name", "")).strip()
        self.household = str(row.get("Household", "")).strip() or self.name
        self.email = str(row.get("Email", "")).strip()
        self.address = str(row.get("Address", "")).strip()
        self.active = truthy(row.get("Active", False))
        # Every remaining column is a potential opt-in flag, looked up by the
        # Rotations tab. Keeping them in a dict means adding a rotation never
        # requires adding an attribute here.
        self.flags = {str(k).strip(): truthy(v) for k, v in row.items()}

    def opted_into(self, column: str) -> bool:
        """A blank Opt-in column on the Rotations tab means everyone qualifies."""
        if not column:
            return True
        return self.flags.get(column, False)

    def __repr__(self) -> str:
        return f"<Person {self.name!r} household={self.household!r}>"


class Roster:
    """The People tab, plus the household view of it.

    Sheet row order is rotation order, so everything here preserves it.
    """

    def __init__(self, rows: List[Dict[str, object]]):
        self.people = [Person(r) for r in rows if str(r.get("Name", "")).strip()]

    def active_people(self, opt_in_column: str = "") -> List[str]:
        return [p.name for p in self.people
                if p.active and p.opted_into(opt_in_column)]

    def active_households(self, opt_in_column: str = "") -> List[str]:
        """Distinct households, in the order their first member appears."""
        seen: List[str] = []
        for person in self.people:
            if not (person.active and person.opted_into(opt_in_column)):
                continue
            if person.household not in seen:
                seen.append(person.household)
        return seen

    def households(self) -> List[str]:
        seen: List[str] = []
        for person in self.people:
            if person.household not in seen:
                seen.append(person.household)
        return seen

    def address_for(self, household: str) -> str:
        """The first non-empty address among a household's members."""
        key = household.strip().lower()
        for person in self.people:
            if person.household.strip().lower() == key and person.address:
                return person.address
        return ""

    def emails(self) -> List[str]:
        return [p.email for p in self.people if p.email]
