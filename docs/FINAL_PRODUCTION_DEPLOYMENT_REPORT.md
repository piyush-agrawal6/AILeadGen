# Production deployment report

Candidate source: `b11d753a0dcaa9f51f65bdb1070722d51304dc71`.

- Full backend1065 passed, one explicit live-mail skip; frontend161 units, types/build and10 browser checks pass.
- Seven responsive widths:320/390/768/1024/1280/1440/1920px. Selected desktop/mobile screenshots visually inspected. Two additional fixture interaction recordings passed.
- Exact-source Cloud Build:`ed2a4891-00e0-4685-a72d-d9552afc9f75`.
- Existing Vercel candidate:`dpl_3TW6FF46rJr5cUE4nmbGmZagjVBX`, READY, sourceb11d753; custom domain not yet promoted at this checkpoint.
- API/worker staging and controlled real-data acceptance are in progress. Existing live API remains revision00138-suf/source0077fe3 until an explicit successful promotion is recorded.

No production migration/reset/delete, secret replacement, OAuth change, hosting move, public admission, live outreach or payment activation has occurred. Fresh backup/restore and preservation evidence remain available. The separate owner `planebyte-website/` directory was not staged or changed.

The final release/remaining limitations are maintained in `PLANEBYTE_PRODUCTION_RELEASE_REPORT.md`. A READY preview or passing fixture run does not establish real worker/provider acceptance or public paid readiness.
