# Others Contract and Non-Breaking Migration Plan

## Objective
Introduce a controlled, structured fallback for non-canonical attributes while preserving all existing behavior.

## Canonical Contract
The fallback lives at `unmappedData.attributes[]`.

Each record follows this structure:

- `attributeId`: unique id
- `originalLabel`: original source label
- `normalizedLabel`: normalized grouping key
- `extractedValue`: preserved raw value
- `valueType`: `string|number|integer|boolean|array|object`
- `source`: pipeline/source id
- `sourceSection`: source section/bucket
- `sourcePath`: path in extracted payload
- `confidence`: optional score
- `mappingStatus`: `unmapped|low_confidence|ambiguous|deferred`
- `firstSeenAt`: first capture timestamp
- `lastSeenAt`: latest capture timestamp
- `occurrenceCount`: deduplicated frequency counter
- `promotionCandidate`: schema-promotion flag
- `reviewStatus`: `pending|reviewed|promoted|rejected`

## Backward Compatibility Rules
1. Keep legacy source buckets under `unmappedData.<source>` unchanged.
2. Dual-write new unmapped values into `unmappedData.attributes[]`.
3. Do not remove existing keys used by current preview/review/export flows.

## Migration Strategy (No Breaking Changes)
1. Write path migration (now):
   - Any new unmapped value is written to both legacy and structured contracts.
2. Read path migration (later):
   - Existing consumers continue reading legacy buckets.
   - New analytics and governance jobs read `unmappedData.attributes[]`.
3. Historical backfill (incremental):
   - On session load/save, run a lightweight normalizer that mirrors legacy unmapped buckets into `attributes[]`.
   - Keep operation idempotent via source+path+value dedup.
4. Governance rollout:
   - Weekly frequency report grouped by `normalizedLabel`.
   - Promote only after recurrence + business validation.

## Promotion Policy (Recommended)
A candidate can be promoted into canonical schema only if:

- Appears in at least N distinct CVs.
- Has stable meaning across source formats.
- Is required by downstream business workflows.
- Has low ambiguity and acceptable extraction quality.

## Operational Notes
- Keep canonical schema stable for downstream reliability.
- Treat `unmappedData.attributes[]` as controlled extension layer.
- Preserve full traceability with source metadata and timestamps.
