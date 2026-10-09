"""Parse input.csv into one example-shaped CSV per database.

Run: python parse_records.py
Defaults: input.csv -> output/yyyymmdd_hhss/<database>.csv
Each record belongs to its alphabetically first database (case-insensitive).
Unavailable bibliographic fields remain blank; no external lookup is performed.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path
from typing import Mapping


def split_list(value: str) -> tuple[str, ...]:
    """Parse the input's semicolon-separated fields."""
    return tuple(part.strip() for part in value.split(";") if part.strip())


@dataclass(frozen=True)
class SourceRecord:
    """All columns from the original record; parsed lists are immutable."""

    id: str
    sept_id: str
    year: int | None
    title: str
    authors: tuple[str, ...]
    venue: str
    document_type: str
    databases: tuple[str, ...]
    doi: str
    abstract: str
    keywords: tuple[str, ...]
    language: str
    screening_flags: str
    stage: str
    assigned_to: str
    screener_1: str
    screener_2: str
    decision: str
    exclusion_reason: str
    excluded_at_stage: str
    notes: str

    @classmethod
    def from_csv_row(cls, row: Mapping[str, str]) -> SourceRecord:
        year = row["Year"].strip()
        return cls(
            id=row["ID"],
            sept_id=row["Sept ID"],
            year=int(year) if year else None,
            title=row["Title"],
            authors=split_list(row["Authors"]),
            venue=row["Venue"],
            document_type=row["Document type"],
            databases=split_list(row["Found in"]),
            doi=row["DOI"],
            abstract=row["Abstract"],
            keywords=split_list(row["Keywords"]),
            language=row["Language"],
            screening_flags=row["Screening flags"],
            stage=row["Stage"],
            assigned_to=row["Assigned to"],
            screener_1=row["Screener 1"],
            screener_2=row["Screener 2"],
            decision=row["Decision"],
            exclusion_reason=row["Exclusion reason"],
            excluded_at_stage=row["Excluded at stage"],
            notes=row["Notes"],
        )

    @property
    def database(self) -> str:
        if not self.databases:
            raise ValueError(f"Record {self.id!r} has no database in 'Found in'")
        return min(self.databases, key=lambda name: (name.casefold(), name))


@dataclass(frozen=True)
class OutputRecord:
    """Column names and order match excel-example.csv."""

    key: str
    title: str
    authors: str
    journal: str
    issn: str
    volume: str
    issue: str
    pages: str
    year: str
    publisher: str
    url: str
    abstract: str
    notes: str
    doi: str
    keywords: str

    @classmethod
    def from_record(cls, record: SourceRecord) -> OutputRecord:
        """Convert an old-format record to the new format.

        Remove trailing numeric author identifiers and use the example's
        ' and ' separator. Venue maps to journal, including conference venues.
        Source-only screening metadata remains available on SourceRecord.
        """
        authors = tuple(
            re.sub(r"\s*\(\d+\)$", "", author) for author in record.authors
        )
        return cls(
            key=record.id,
            title=record.title,
            authors=" and ".join(authors),
            journal=record.venue,
            issn="",
            volume="",
            issue="",
            pages="",
            year=str(record.year) if record.year is not None else "",
            publisher="",
            url="",
            abstract=record.abstract,
            notes=record.notes,
            doi=record.doi,
            keywords=";".join(record.keywords),
        )


def read_records(path: Path) -> list[SourceRecord]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        records = []
        for row in reader:
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("row has a different number of fields than the header")
                records.append(SourceRecord.from_csv_row(row))
            except (KeyError, ValueError) as error:
                raise ValueError(f"{path}, near line {reader.line_num}: {error}") from error
        return records


def write_records(records: list[SourceRecord], output_root: Path) -> Path:
    grouped: dict[str, list[OutputRecord]] = defaultdict(list)
    for record in records:
        grouped[record.database].append(OutputRecord.from_record(record))

    # Keep database names readable, replacing characters unsafe in filenames.
    filenames = {
        database: re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", database).rstrip(". ") + ".csv"
        for database in grouped
    }
    if len({name.casefold() for name in filenames.values()}) != len(filenames):
        raise ValueError("Database names produce colliding output filenames")

    # %H%S follows the requested hhss format: hour and second, without minutes.
    directory = output_root / datetime.now().strftime("%Y%m%d_%H%S")
    directory.mkdir(parents=True, exist_ok=False)
    columns = [field.name for field in fields(OutputRecord)]
    for database in sorted(grouped, key=str.casefold):
        with (directory / filenames[database]).open(
            "w", newline="", encoding="utf-8"
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(asdict(record) for record in grouped[database])
    return directory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, default=Path("input.csv"))
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args()
    records = read_records(args.input)
    directory = write_records(records, args.output)
    print(f"Wrote {len(records)} records to {directory}")


if __name__ == "__main__":
    main()
