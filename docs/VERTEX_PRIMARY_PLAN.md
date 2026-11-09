# Active Vertex primary migration

Latest owner steering: Vertex primary using ADC/service identity in projectquerryside/global/modelgemini-3.6-flash; existing single Gemini Developer API key remains fallback; deterministic evidence templates remain final fallback. Preserve40-lead batching/cache/idempotency/splitting, campaigns, SMTP/IMAP/replies and schedules. No service-account JSON, credential path, key rotation or exposed key values/fragments.

IAM inspected before Vertex code changes: Vertex API enabled, localADCavailable, API actuallyusesleadengine-api-sa, coreworkerleadengine-worker-sa, isolatedsourceworkerleadengine-acquisition-sa. Allthree initiallylackedroles/aiplatform.user. Automaticapprovalreviewinitiallyrejectedgrantsbecauseownerattachmentnamedanotheridentity; ownerhasnowexplicitlyapprovedtheseexactthreegrants. Preserveattachedidentitiesandaddonlythisrolewhereabsent.

Extend existingapp.acquisition.ai abstraction/transport. A central router owns provider order, inference-only error normalization, bounded retries and independent cooldowns. Vertex outage tries samecompletebatchonGeminibeforeanysplit; invalidstructuredresponsesmaysplit; application/programmingexceptionsmustpropagateinstead of providerfallback. Existing intent/mappingtasksreuse the router aftercopyprovesstable; do notcreate nonexistentIntentRadarfeatures.

Acceptance: actuallocalADC1→5→10→40checks, exactly40matchedIDs/oneVertexrequest; mockVertex→Geminisucccess andboth→deterministic; PostgreSQL/cache/recovery/regressions; productionCloudRunserviceidentitysmoke; progressive10→40pendingcopy; reusecompletedfirstowneremail. Originalfive-dayexperimentandremainingfourcontrolledemailsarenotLIVEuntilallgatespass; November2startmustnot silentlymove.

PriorGemini-onlyprobe returnedHTTP402RESOURCE_EXHAUSTED onnewrootkey. Thisisfallback-providerdegradation,not a reason to blockhealthyVertex. GenuineownerreplytofirstcontrolledmessagewasverifiedPOSITIVEwithcorrectattribution. Schema14live; reusegenerationJSON/cache/events/preferenceswithoutanunnecessarymigration.
