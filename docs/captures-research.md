# Capture Research — Vendor API References

References used to author synthetic HAR fixtures for the pilot DDFs.

## Microsoft Calendar (Graph API)

- [Microsoft Graph REST API v1.0](https://learn.microsoft.com/en-us/graph/api/overview?view=graph-rest-1.0)
- [OAuth 2.0 client credentials flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-client-creds-grant-flow)
- [List calendarView](https://learn.microsoft.com/en-us/graph/api/calendar-list-calendarview?view=graph-rest-1.0)
- [List places (rooms)](https://learn.microsoft.com/en-us/graph/api/place-list?view=graph-rest-1.0)
- [Change notifications](https://learn.microsoft.com/en-us/graph/api/resources/webhooks?view=graph-rest-1.0)

### Confidence Level
**High** — Microsoft Graph API is fully documented with public reference.

## Daikin Stylish (Onecta API)

- [pydaikin library](https://pypi.org/project/pydaikin/) — community-maintained Python client
- [pydaikin source code](https://github.com/fredrike/pydaikin) — reverse-engineered API endpoints
- Daikin Onecta IDP: `https://idp.onecta.daikineurope.com/`
- Daikin Onecta API: `https://api.onecta.daikineurope.com/`

### Known Endpoints (from pydaikin)
- `GET /v1/sites` — list sites/appliances
- `GET /v1/gateway-devices/{id}` — full device status
- `PATCH /v1/gateway-devices/{id}/management-points/climateControl/characteristics/{char}` — set characteristic

### Confidence Level
**Medium** — No official Daikin API documentation. Based on community reverse-engineering.
Sprint 2 hardware recorder will produce real captures that supersede these synthetics.

## Notes

- Edge cases in synthetic HARs: empty arrays, null fields, error responses (503)
- All HAR entries include `comment` fields explaining the scenario
- Date/time values use realistic UTC timestamps
