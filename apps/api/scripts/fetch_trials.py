import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

ROOT_DIR = Path(__file__).resolve().parents[3]
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

CONDITIONS = [
    "breast cancer",
    "lung cancer",
    "prostate cancer",
    "colorectal cancer",
    "skin cancer",
    "leukemia",
    "lymphoma",
    "diabetes",
    "type 1 diabetes",
    "type 2 diabetes",
    "depression",
    "anxiety",
    "asthma",
    "alzheimer",
    "parkinson",
    "heart disease",
    "hypertension",
    "stroke",
    "obesity",
    "arthritis",
    "migraine",
    "multiple sclerosis",
    "hiv",
    "covid-19",
    "kidney disease",
    "liver disease",
    "epilepsy",
    "autism",
    "schizophrenia",
    "copd",
]


def clean_trial(study: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    protocol = study.get("protocolSection", {})

    identification = protocol.get("identificationModule", {})
    status_module = protocol.get("statusModule", {})
    description = protocol.get("descriptionModule", {})
    conditions_module = protocol.get("conditionsModule", {})
    design = protocol.get("designModule", {})
    arms = protocol.get("armsInterventionsModule", {})
    eligibility = protocol.get("eligibilityModule", {})
    contacts_locations = protocol.get("contactsLocationsModule", {})

    nct_id = identification.get("nctId")
    if not nct_id:
        return None

    interventions = []
    for item in arms.get("interventions", []) or []:
        name = item.get("name")
        if name:
            interventions.append(name)

    locations = []
    for loc in contacts_locations.get("locations", []) or []:
        locations.append(
            {
                "facility": loc.get("facility"),
                "city": loc.get("city"),
                "state": loc.get("state"),
                "country": loc.get("country"),
                "zip": loc.get("zip"),
            }
        )

    phases = design.get("phases") or []
    phase = phases[0] if phases else None

    return {
        "nct_id": nct_id,
        "title": identification.get("briefTitle", ""),
        "status": status_module.get("overallStatus", ""),
        "phase": phase,
        "conditions": conditions_module.get("conditions", []) or [],
        "interventions": interventions,
        "summary": description.get("briefSummary", ""),
        "eligibility": eligibility.get("eligibilityCriteria", ""),
        "sex": eligibility.get("sex"),
        "minimum_age": eligibility.get("minimumAge"),
        "maximum_age": eligibility.get("maximumAge"),
        "locations": locations,
        "source_url": f"https://clinicaltrials.gov/study/{nct_id}",
        "last_update_date": status_module.get("lastUpdateSubmitDate"),
    }


def fetch_trials_for_condition(
    condition: str,
    page_size: int = 1000,
    max_pages: int = 3,
) -> List[Dict[str, Any]]:
    all_cleaned = []
    page_token = None

    for page in range(max_pages):
        params = {
            "query.cond": condition,
            "filter.overallStatus": "RECRUITING,NOT_YET_RECRUITING",
            "pageSize": page_size,
            "format": "json",
            "countTotal": "true",
        }

        if page_token:
            params["pageToken"] = page_token

        print(f"  page {page + 1}...", flush=True)

        response = requests.get(BASE_URL, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()

        safe_condition = condition.replace(" ", "_").replace("/", "_")
        raw_path = RAW_DIR / f"{safe_condition}_page_{page + 1}.json"
        raw_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        studies = data.get("studies", [])
        for study in studies:
            cleaned = clean_trial(study)
            if cleaned:
                all_cleaned.append(cleaned)

        page_token = data.get("nextPageToken")
        if not page_token:
            break

        time.sleep(0.4)

    return all_cleaned


def main():
    all_trials = []
    seen = set()

    for condition in CONDITIONS:
        print(f"\nFetching condition: {condition}", flush=True)

        try:
            trials = fetch_trials_for_condition(condition)
        except Exception as error:
            print(f"  ERROR fetching {condition}: {error}", flush=True)
            continue

        added = 0
        for trial in trials:
            if trial["nct_id"] not in seen:
                seen.add(trial["nct_id"])
                all_trials.append(trial)
                added += 1

        print(f"  added {added} unique trials", flush=True)

    output_path = PROCESSED_DIR / "trials.json"
    output_path.write_text(json.dumps(all_trials, indent=2), encoding="utf-8")

    print("\nDone.")
    print(f"Saved {len(all_trials)} unique trials to {output_path}")


if __name__ == "__main__":
    main()