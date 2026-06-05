# Data Classification

| Data | Classification | Handling |
| --- | --- | --- |
| Source code and public docs | Internal | Normal repository controls |
| Ontology schema only | Confidential | Keep in local workspace or approved repository |
| Customer conversations and examples | Confidential | Mask PII, encrypted filesystem, limited sharing |
| `workshop.kuzu` | Confidential | Local encrypted disk, delete after retention period |
| `exports/report/*` | Confidential | Share only with approved participants |
| `exports/neptune.cypher`, `exports/bulk/*.csv` | Confidential | Upload only to encrypted S3 buckets with Block Public Access |
| API keys and tokens | Restricted | Environment variables or secret manager only |

Retention:

* Default local workshop retention is 30 days unless the customer requires a shorter period.
* Delete generated exports and the Kuzu database after handoff acceptance.
* For regulated data, obtain customer approval before any LLM call.
