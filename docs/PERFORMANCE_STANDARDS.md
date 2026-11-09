# Performance standards

Keep public auth independent of private data polling, heavy reports and provider calls. The auth browser check asserts zero private API requests. Use local fonts and code-native SVG; respect reduced motion and fixed image dimensions. Query only paginated/scoped data and avoid N+1 loops.

Existing workers provide bounded acquisition, rendering and sync. Keep slow work off request paths. Preserve cancellation, idempotency, timeouts and safety checks while optimizing. Provider failures should not block unrelated page reads.

Measured here: auth browser suite completed in29.1s including local app setup/navigation; this is a test duration, not LCP/INP or a throughput measurement. Core Web Vitals and concurrent-user baselines remain staging work. Do not claim scalability from a successful build.
