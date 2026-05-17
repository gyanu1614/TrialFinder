import requests
from typing import Any, Dict, List, Optional

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"


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


def fetch_live_trials(
    query: str,
    condition: Optional[str] = None,
    page_size: int = 50,
) -> List[Dict[str, Any]]:
    query_clean = query.replace("car-t", "CAR T").replace("CAR-T", "CAR T")

    attempts = []

    if condition:
        attempts.append(
            {
                "format": "json",
                "pageSize": page_size,
                "query.cond": condition,
                "query.term": query_clean,
                "filter.overallStatus": "RECRUITING,NOT_YET_RECRUITING",
            }
        )
        attempts.append(
            {
                "format": "json",
                "pageSize": page_size,
                "query.cond": condition,
                "filter.overallStatus": "RECRUITING,NOT_YET_RECRUITING",
            }
        )

    attempts.append(
        {
            "format": "json",
            "pageSize": page_size,
            "query.term": query_clean,
            "filter.overallStatus": "RECRUITING,NOT_YET_RECRUITING",
        }
    )

    attempts.append(
        {
            "format": "json",
            "pageSize": page_size,
            "query.term": query_clean,
        }
    )

    for params in attempts:
        response = requests.get(BASE_URL, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        studies = data.get("studies", [])

        cleaned_trials = []
        for study in studies:
            cleaned = clean_trial(study)
            if cleaned:
                cleaned_trials.append(cleaned)

        if cleaned_trials:
            return cleaned_trials

    return []