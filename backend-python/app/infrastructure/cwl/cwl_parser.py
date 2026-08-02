import yaml


def inject_description(cwl_content: str, description: str | None) -> str:
    doc = yaml.safe_load(cwl_content)
    if description:
        doc["doc"] = description
    else:
        doc.pop("doc", None)
    return yaml.dump(doc, default_flow_style=False, sort_keys=False, width=float("inf"))