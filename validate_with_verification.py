#!/usr/bin/env python3
"""
Validate an HL7 v2 XML message with Gazelle EVS and print parseable results.

This module is used both as a CLI by dashboard_app.py and as an import target by
cli_test_debug.py.
"""
import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree as ET

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("GAZELLE_BASE_URL", "https://testing.ehealthireland.ie").rstrip("/")
VALIDATION_ENDPOINT = f"{BASE_URL}/evs/rest/validations"
VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() in ("1", "true", "yes")

VALIDATORS = {
    "ADT^A01": "1.3.6.1.4.1.12559.11.35.10.1.7",
    "ADT^A03": "1.3.6.1.4.1.12559.11.35.10.1.9",
    "REF^I12": "1.3.6.1.4.1.12559.11.35.10.1.20",
    "SIU^S12": "1.3.6.1.4.1.12559.11.35.10.1.21",
    "SIU^S13": "1.3.6.1.4.1.12559.11.35.10.1.22",
    "ORU^R01": "1.3.6.1.4.1.12559.11.35.10.1.12",
}

MESSAGE_TYPES = {
    "ADT_A01": "ADT^A01",
    "ADT_A03": "ADT^A03",
    "REF_I12": "REF^I12",
    "SIU_S12": "SIU^S12",
    "SIU_S13": "SIU^S13",
    "RRI_I12": "RRI^I12",
    "ORU_R01": "ORU^R01",
}


def detect_message_type(file_path):
    """Detect HL7 v2 XML message type from the root element."""
    content = Path(file_path).read_bytes()
    root = ET.fromstring(content)
    root_tag = root.tag.split("}", 1)[1] if "}" in root.tag else root.tag
    return MESSAGE_TYPES.get(root_tag)


def _auth_headers():
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    api_key = os.getenv("GAZELLE_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"GazelleAPIKey {api_key}"
    return headers


def _extract_submission(location):
    parsed = urlparse(location or "")
    query = parse_qs(parsed.query)
    oid = None
    if "/validations/" in parsed.path:
        oid = parsed.path.rsplit("/validations/", 1)[1].split("/", 1)[0]
    elif parsed.path:
        oid = parsed.path.rstrip("/").rsplit("/", 1)[-1]

    return {
        "oid": oid,
        "privacy_key": query.get("privacyKey", [""])[0],
        "location": location,
    }


def submit_validation(file_path):
    """Submit a file to Gazelle and return submission metadata."""
    try:
        path = Path(file_path)
        message_type = detect_message_type(path)
        validator = VALIDATORS.get(message_type)
        if not validator:
            return None, f"No configured Gazelle validator for message type {message_type or 'Unknown'}"

        payload = {
            "objects": [{
                "originalFileName": path.name,
                "content": base64.b64encode(path.read_bytes()).decode("ascii"),
            }],
            "validationService": {
                "name": "Gazelle HL7v2.x validator",
                "validator": validator,
            },
        }

        response = requests.post(
            VALIDATION_ENDPOINT,
            json=payload,
            headers=_auth_headers(),
            timeout=30,
            verify=VERIFY_SSL,
        )

        if response.status_code not in (201, 202):
            return None, f"Gazelle submission failed ({response.status_code}): {response.text[:500]}"

        submission = _extract_submission(response.headers.get("Location"))
        submission["message_type"] = message_type
        submission["validator"] = validator
        return submission, None
    except Exception as e:
        return None, str(e)


def check_validation_status(oid, attempts=10, delay=1.5):
    """Fetch the Gazelle XML report for an existing validation OID."""
    api_key = os.getenv("GAZELLE_API_KEY", "").strip()
    headers = {"Accept": "application/xml"}
    if api_key:
        headers["Authorization"] = f"GazelleAPIKey {api_key}"

    url = f"{BASE_URL}/evs/rest/validations/{oid}/report"
    last_error = None
    for _ in range(attempts):
        try:
            response = requests.get(url, headers=headers, timeout=30, verify=VERIFY_SSL)
            if response.status_code == 200 and response.text.strip():
                return response.text, None
            last_error = f"Report fetch failed ({response.status_code}): {response.text[:300]}"
        except Exception as e:
            last_error = str(e)
        time.sleep(delay)
    return None, last_error or "Report was not available"


def _constraint_issue(constraint):
    desc_elem = constraint.find("gvr:constraintDescription", XML_NS)
    loc_elem = constraint.find("gvr:locationInValidatedObject", XML_NS)
    type_elem = constraint.find("gvr:constraintType", XML_NS)
    return {
        "description": desc_elem.text if desc_elem is not None else "Unknown",
        "location": loc_elem.text if loc_elem is not None else "Unknown",
        "type": type_elem.text if type_elem is not None else "Unknown",
        "priority": constraint.get("priority", ""),
        "severity": constraint.get("severity", ""),
    }


XML_NS = {"gvr": "http://validationreport.gazelle.ihe.net/"}


def parse_validation_result(xml_report):
    """Parse a Gazelle validation XML report into dashboard-friendly fields."""
    try:
        root = ET.fromstring(xml_report)
        status = "UNKNOWN"

        result_elem = root.find(".//gvr:validationTestResult", XML_NS)
        if result_elem is not None and result_elem.text:
            status = result_elem.text.strip().upper()

        mandatory_errors = []
        warnings = []

        for constraint in root.findall(".//gvr:constraint", XML_NS):
            if constraint.get("testResult") != "FAILED":
                continue

            issue = _constraint_issue(constraint)
            priority = issue["priority"]
            severity = issue["severity"]

            if priority == "MANDATORY" and severity == "ERROR":
                mandatory_errors.append(issue)
            elif priority == "RECOMMENDED" or severity == "WARNING":
                warnings.append(issue)

        if status == "UNKNOWN":
            status = "FAILED" if mandatory_errors else "PASSED"

        return {
            "status": status,
            "mandatory_errors": mandatory_errors,
            "warnings": warnings,
        }, None
    except Exception as e:
        return None, str(e)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate an HL7 v2 XML file with Gazelle EVS")
    parser.add_argument("file_path")
    parser.add_argument("--warnings", action="store_true", help="Print warning details")
    args = parser.parse_args(argv)

    submission, error = submit_validation(args.file_path)
    if error:
        print(f"ERROR: {error}")
        return 1

    xml_report, error = check_validation_status(submission["oid"])
    if error:
        print(f"ERROR: {error}")
        return 1

    parsed, error = parse_validation_result(xml_report)
    if error:
        print(f"ERROR: {error}")
        return 1

    report_url = f"{BASE_URL}/evs/report.seam?oid={submission['oid']}"
    if submission.get("privacy_key"):
        report_url += f"&privacyKey={submission['privacy_key']}"

    errors = parsed["mandatory_errors"]
    warnings = parsed["warnings"]

    print(f"GAZELLE_OID={submission['oid']}")
    print(f"OID: {submission['oid']}")
    print(f"Message Type: {submission.get('message_type') or 'Unknown'}")
    print(f"Status: {parsed['status']}")
    print(f"Errors: MANDATORY: {len(errors)})")
    print(f"Warnings: {len(warnings)}")
    print(f"Report: {report_url}")
    print("GAZELLE_ERRORS_JSON=" + json.dumps(errors, ensure_ascii=False))
    print("GAZELLE_WARNINGS_JSON=" + json.dumps(warnings, ensure_ascii=False))

    if errors:
        print("\nERROR DETAILS")
        for idx, issue in enumerate(errors, 1):
            print(f"Error #{idx}: {issue.get('description', 'Unknown')}")
            print(f"Location: {issue.get('location', 'Unknown')}")

    if args.warnings and warnings:
        print("\nWARNING DETAILS")
        for idx, issue in enumerate(warnings, 1):
            print(f"Warning #{idx}: {issue.get('description', 'Unknown')}")
            print(f"Location: {issue.get('location', 'Unknown')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
