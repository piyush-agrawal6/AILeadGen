-- Radar-only lineage. This removes disabled product flags, never a workspace,
-- membership, identity or entitlement. Reject unknown dependencies under lock.
LOCK TABLE organization_products IN SHARE ROW EXCLUSIVE MODE;
LOCK TABLE discovery_searches IN ACCESS EXCLUSIVE MODE;
DO $$
BEGIN
 IF EXISTS (SELECT 1 FROM organization_products WHERE product='LEADGEN' AND enabled<>0)
 OR EXISTS (SELECT 1 FROM pg_constraint WHERE contype='f' AND confrelid='organization_products'::regclass)
 OR EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid='organization_products'::regclass AND NOT tgisinternal)
 OR EXISTS (SELECT 1 FROM pg_rewrite WHERE ev_class='organization_products'::regclass AND ev_type='4') THEN
  RAISE EXCEPTION 'Lead product retirement requires dependency review';
 END IF;
 IF EXISTS (SELECT 1 FROM discovery_searches)
 OR EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid='discovery_searches'::regclass AND NOT tgisinternal)
 OR EXISTS (SELECT 1 FROM pg_policy WHERE polrelid='discovery_searches'::regclass)
 OR EXISTS (SELECT 1 FROM pg_inherits WHERE inhparent='discovery_searches'::regclass OR inhrelid='discovery_searches'::regclass) THEN
  RAISE EXCEPTION 'Legacy prospect-search table requires retention review';
 END IF;
END $$;
DELETE FROM organization_products WHERE product='LEADGEN' AND enabled=0;
-- Empty prospecting search definitions, not intent_discoveries or saved research.
-- External references must block retirement rather than cascade.
DROP TABLE discovery_searches RESTRICT;

UPDATE intent_schema_metadata SET structure_manifest_sha256='77595ec0a156d246d0a9c1baa9ea0862dcd2290e1f21cbca3069c1776e7cce50' WHERE singleton=1;
