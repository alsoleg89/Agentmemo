"""Purpose/role vocabulary normalizer.

Maps verb stems and role nouns to canonical purpose categories used in
canonical_surface enrichment.  Generic English vocabulary — no proper nouns,
no dataset-specific values.
"""

from __future__ import annotations

# stem (lowercase substring) → canonical purpose label
STEM_TO_PURPOSE: dict[str, str] = {
    # Mentoring / teaching
    "mentor": "mentoring",
    "tutor": "mentoring",
    "coach": "mentoring",
    "counsel": "mentoring",
    "advise": "mentoring",
    "guid": "mentoring",
    # Children / youth
    " child": "children",
    " kid": "children",
    "youth": "children",
    "student": "children",
    "teen": "children",
    "juvenile": "children",
    # Teaching / instruction
    "teach": "teaching",
    "instruct": "teaching",
    "lectur": "teaching",
    "educat": "teaching",
    # Helping / support
    "help": "helping",
    "support": "helping",
    "assist": "helping",
    "aid ": "helping",
    "care for": "helping",
    # Speech / presentation
    "speech": "speech",
    "present": "speech",
    "speak ": "speech",
    "talk ": "speech",
    "address": "speech",
    # Volunteering
    "volunteer": "volunteering",
    "nonprofit": "volunteering",
    "charity": "volunteering",
    "donate": "volunteering",
    # Programs / initiatives
    "program": "program",
    "initiative": "program",
    "project": "program",
    "campaign": "program",
    # Community
    "communit": "community",
    "neighbor": "community",
    "local ": "community",
    "outreach": "community",
    # School events
    "school": "school_event",
    "classroom": "school_event",
    "campus": "school_event",
}
