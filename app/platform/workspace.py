"""Ownership checks for persisted background-work resources.

Callers obtain organization from verified membership or an owned job record,
never from arbitrary provider data or a submitted company object.
"""


def business_workspace(conn, business, *, organization=None, campaign_id=None):
    row = conn.execute(
        "SELECT b.run_id,p.organization_id,p.campaign_id FROM businesses b "
        "JOIN pipeline_runs p ON p.id=b.run_id WHERE b.id=?",
        (business.id,),
    ).fetchone()
    if not row or not row[1] or row[0] != business.run_id:
        raise ValueError("Business requires a persisted workspace-owned run")
    if organization is not None and row[1] != organization:
        raise ValueError("Business does not belong to this workspace")
    if campaign_id is not None:
        campaign = conn.execute(
            "SELECT organization_id FROM scan_campaigns WHERE id=?", (campaign_id,)
        ).fetchone()
        if not campaign or campaign[0] != row[1] or row[2] != campaign_id:
            raise ValueError("Business and campaign ownership do not match")
    return row[1]
