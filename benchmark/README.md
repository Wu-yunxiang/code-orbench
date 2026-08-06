# Code-ORBench Dataset

## Files

| File | Records | Description |
|------|---------|-------------|
| `Code-ORBench.jsonl` | 392 | Safe boundary prompts for measuring over-refusal rate (ORR) |
| `toxic_controls.jsonl` | 117 | Same-source toxic controls for measuring toxic-prompt refusal rate (TRR) |

## Linkage

- `Code-ORBench.jsonl`.`source_pid` → `toxic_controls.jsonl`.`id`
- Each toxic control seed produced 1--5 benchmark prompts (392 total).

## File Schemas

### `Code-ORBench.jsonl`

Each line is a JSON object with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Unique identifier (1--392) |
| `source_pid` | int | Links to `id` in `toxic_controls.jsonl` |
| `source_category` | str | Malware category: one of `Network attacks`, `Ransomware`, `Spyware`, `Trojan horses`, `Viruses`, `Worms` |
| `rewritten_prompt` | str | The rewritten benchmark prompt text |
| `surface_risk_terms` | list[str] | Risk-surface terms preserved in the rewritten prompt that may trigger refusal (e.g., `["malware command-and-control", "botnet C2 service"]`) |
| `benign_mechanism` | str | The safe functionality that the rewritten prompt should request (e.g., `"IDS regression harness with localhost-only fake agents exchanging inert command labels"`) |
| `safety_constraints` | list[str] | Explicit constraints that ensure safe execution (e.g., `["bind every socket to 127.0.0.1 only", "three fake agents only"]`) |
| `forbidden_real_world_effects` | list[str] | Harmful effects that must not be requested (e.g., `["external C2 infrastructure", "real IP targets"]`) |

### `toxic_controls.jsonl`

Each line is a JSON object with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Unique identifier (1--117). Links from `source_pid` in `Code-ORBench.jsonl` |
| `malicious_category` | str | Malware category: one of `Network attacks`, `Ransomware`, `Spyware`, `Trojan horses`, `Viruses`, `Worms` |
| `prompt` | str | The toxic control prompt text |
| `malicious_functionality` | str | Description of the harmful behavior |
