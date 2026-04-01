"""Extract sample IDs and process names from SLURM job names."""

import re

# Known patient/sample ID patterns (order matters — check specific first)
# s_C_ IDs: alphanumeric only after the prefix (no underscores/dashes)
# P- IDs: alphanumeric with dash-separated suffixes (e.g. P-0000001-T01-TEST)
# C- IDs: alphanumeric only (no underscores/dashes)
_KNOWN_ID_PATTERNS = [
    re.compile(r"s_C_[A-Za-z0-9]+"),           # s_C_ prefixed IDs
    re.compile(r"P-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*"),  # DMP IDs with dash suffixes
    re.compile(r"C-[A-Za-z0-9]+"),             # C- prefixed IDs
]

# Parenthesized content (likely a sample identifier)
_PAREN_PATTERN = re.compile(r"\(([^)]+)\)")

# Nextflow pipeline prefix: nf-NFCORE_PIPELINE_PIPELINE_
_NF_PREFIX = re.compile(r"^nf-(?:[A-Z0-9]+_)*?([A-Z0-9]+)_\1_")


def extract_sample_id(job_name: str) -> str | None:
    """Extract the sample/patient ID from a job name.

    Returns the first matched ID, or None if no ID pattern is found.
    Priority: known ID patterns > parenthesized content.
    """
    # Check parenthesized content first (most specific context)
    paren_match = _PAREN_PATTERN.search(job_name)
    if paren_match:
        content = paren_match.group(1)
        # Check if it contains a known ID pattern
        for pattern in _KNOWN_ID_PATTERNS:
            m = pattern.search(content)
            if m:
                return m.group(0)
        # If parenthesized content looks like an ID (has alphanumeric + dashes, 6+ chars)
        if len(content) >= 6 and re.search(r"[A-Z0-9]", content):
            return content

    # Check for known ID patterns anywhere in the name
    for pattern in _KNOWN_ID_PATTERNS:
        m = pattern.search(job_name)
        if m:
            return m.group(0)

    return None


def extract_process_name(job_name: str) -> str:
    """Extract the process/step name from a job name.

    Strips sample IDs and common prefixes (nf-, pipeline name repetitions).
    Falls back to the full job_name if nothing meaningful remains.
    """
    name = job_name

    # Remove parenthesized content (sample IDs)
    name = _PAREN_PATTERN.sub("", name)

    # Remove Nextflow prefix: nf-NFCORE_PIPELINE_PIPELINE_ → keep what follows
    nf_match = _NF_PREFIX.match(name)
    if nf_match:
        name = name[nf_match.end():]
    elif name.startswith("nf-"):
        name = name[3:]

    # Remove known ID patterns from remaining string
    for pattern in _KNOWN_ID_PATTERNS:
        name = pattern.sub("", name)

    # Clean up: collapse multiple underscores, strip leading/trailing separators
    name = re.sub(r"[_\-]{2,}", "_", name)
    name = name.strip("_- ")

    return name if name else job_name
