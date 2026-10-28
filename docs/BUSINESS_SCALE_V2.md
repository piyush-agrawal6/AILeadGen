# Business scale V2

Version `scale-2.0.1` classifies the observed public footprint: LOCAL 1; SMALL_GROUP 2–5; MID_MARKET 6–25; REGIONAL 26–100; ENTERPRISE above 100 with corroborating multi-city/region or location-page evidence. Registered chain domains/names and evidenced larger franchise networks are KNOWN_CHAIN. A 15-location independent dental group is MID_MARKET and is a default target.

Inputs combine distinct public addresses/cities/regions for the professional domain, sampled location/clinic/branch links and structured location lists. Shared hosting domains are not counted as one corporate group. Counts are observed lower bounds, not claims about total branches. Confidence and reason are exposed. No revenue, employee count or budget is inferred.

Default campaign selection includes Local, Small Group and Mid Market. Regional is optional; Enterprise and Known Chain remain off. Classification is stored per business observation; canonical identity and existing workflow are preserved. Historical observations without a V2 record retain their existing classification.

Commercial fit is separate from opportunity scores: available public contact routes, professional website and footprint support HIGH/MEDIUM; out-of-default chains/enterprise are LOW; insufficient evidence is UNKNOWN. It is an optional workspace sort/filter. Opportunity scoring and the default opportunity sort remain unchanged.

Balanced/high-intent export ordering applies a modest preference (Mid Market +8, Small Group +5, HIGH fit +3) to the existing priority. This does not modify stored opportunity scores or exclude a strong local result.

Missing/single-label website values (including NaN) never count as a professional corporate domain or a shared multi-location footprint. Optional Overture text fields are decoded without converting missing dataframe values into strings.
