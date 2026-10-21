"""Run OpenMetadata's AutoClassificationWorkflow against chosen classifications.

Why this exists: in OpenMetadata 2.0.5 (open source) the built-in
`metadata classify` command hard-codes `classification_filter=[PII]`
(metadata/workflow/classification.py), so tag-level recognizers configured on
any *other* classification are never evaluated, although the TagProcessor
engine supports them. This script reuses the official workflow class and only
changes which classifications are passed to the processor.

Usage (inside the openmetadata/ingestion image):
    python /ext/classify_with.py <workflow.yaml> PIPEDA [OTHER_CLASSIFICATION ...]
"""

import sys

import yaml
from metadata.pii.processor_factory import create_pii_processor
from metadata.workflow.classification import AutoClassificationWorkflow
from metadata.workflow.workflow_output_handler import print_status


class MultiClassificationWorkflow(AutoClassificationWorkflow):
    classification_names: list[str] = []

    def _get_pii_processor(self):
        return create_pii_processor(self.metadata, self.config, classification_filter=self.classification_names)


def main() -> None:
    config_path, *names = sys.argv[1:]
    MultiClassificationWorkflow.classification_names = names or ["PII"]
    with open(config_path, encoding="utf-8") as f:
        workflow = MultiClassificationWorkflow.create(yaml.safe_load(f))
    workflow.execute()
    workflow.raise_from_status()
    print_status(workflow)
    workflow.stop()


if __name__ == "__main__":
    main()
