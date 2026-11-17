-- Record this independent schema lineage, not a replay of old customer migrations.
CREATE TABLE __PLANEBYTE_SCHEMA__.intent_schema_metadata (
 singleton INTEGER PRIMARY KEY CHECK(singleton=1),
 profile TEXT NOT NULL,
 source_baseline INTEGER NOT NULL,
 structure_manifest_sha256 TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP::text)
);
INSERT INTO __PLANEBYTE_SCHEMA__.intent_schema_metadata(singleton,profile,source_baseline,structure_manifest_sha256)
VALUES(1,'intent-radar-v1',51,'41dbe4dc4a7e9cac1a182f5408584d94463bb1154137049d1558db43d1bd25dd');
