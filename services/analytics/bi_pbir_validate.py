"""Validate generated PBIR documents against their declared Microsoft schemas."""
import json
from functools import lru_cache
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from jsonschema import validators
from referencing import Registry, Resource

from services.analytics.bi_pbir import SCHEMA, report_sources


@lru_cache(maxsize=128)
def retrieve(uri):
    if not uri.startswith(SCHEMA):
        raise ValueError("Unexpected schema origin: " + uri)
    for attempt in range(3):
        try:
            request = Request(uri, headers={"User-Agent": "PulseForge-PBIR-validator/1.1", "Accept": "application/json"})
            with urlopen(request, timeout=30) as response:
                return Resource.from_contents(json.load(response))
        except (HTTPError, URLError):
            if attempt == 2:
                raise
            sleep(2 ** attempt)


def main():
    registry = Registry(retrieve=retrieve)
    errors = []
    for path, source in report_sources().items():
        document = json.loads(source)
        schema = retrieve(document["$schema"]).contents
        validator = validators.validator_for(schema)(schema, registry=registry)
        for error in validator.iter_errors(document):
            errors.append(f"{path}: {error.json_path}: {error.message}")
    if errors:
        raise SystemExit("\n".join(errors))
    print("All generated PBIR documents passed declared schema validation")


if __name__ == "__main__":
    main()
