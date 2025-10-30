# UK Sanctions & Electoral Commission API - Integration Guide

## Overview

This API allows you to check if a person or organization appears in:
1. **UK Sanctions List** - 5,656 sanctioned individuals and entities
2. **Electoral Commission Donations** - 89,358 political donations (£1.59 billion)

**Base URL (Production)**: `https://sanlist-production.up.railway.app`
**Base URL (Local)**: `http://localhost:8000`

**Response Time**: ~480ms average
**Rate Limit**: None currently (add if needed)

---

## Quick Start

### Simple Check: Is Someone Sanctioned?

**Endpoint**: `GET /api/entities`

```bash
# Check if "John Smith" is sanctioned
curl "https://sanlist-production.up.railway.app/api/entities?name=John%20Smith&exact=false"
```

**Response Structure**:
```json
{
  "query": "John Smith",
  "count": 0,
  "results": []
}
```

- `count: 0` = **NOT SANCTIONED** ✅
- `count > 0` = **SANCTIONED** ⚠️ (check results array)

---

## Recommended Endpoint: Tenant Screening

**Use this for comprehensive background checks**

### `GET /api/screen-tenant`

Searches **both databases** simultaneously and returns a risk assessment.

#### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | ✅ Yes | Full name to check |
| `date_of_birth` | string | No | Format: `YYYY-MM-DD` |
| `postcode` | string | No | UK postcode for better matching |
| `company_name` | string | No | Company name if checking a business |
| `company_reg` | string | No | Company registration number |
| `exact_match` | boolean | No | `true` for exact match, `false` for fuzzy (default: `false`) |

#### Example Requests

**Basic check:**
```bash
curl "https://sanlist-production.up.railway.app/api/screen-tenant?name=Vladimir%20Putin"
```

**With additional details:**
```bash
curl "https://sanlist-production.up.railway.app/api/screen-tenant?name=John%20Smith&date_of_birth=1990-01-01&postcode=SW1A"
```

**Company check:**
```bash
curl "https://sanlist-production.up.railway.app/api/screen-tenant?company_name=ABC%20Corp&company_reg=12345678"
```

#### Response Structure

```json
{
  "query": "Vladimir Putin",
  "screening_date": "2025-10-29T17:05:21.304060",
  "risk_level": "high",
  "sanctions_matches": [
    {
      "database": "UK_SANCTIONS",
      "matched_name": "PUTIN",
      "unique_id": "RUS0251",
      "entity_type": "Individual",
      "date_listed": "2022-02-25",
      "nationality": "Russia",
      "date_of_birth": "1952-10-07",
      "aliases": [],
      "sanctions": [
        {
          "regime": "The Russia (Sanctions) (EU Exit) Regulations 2019",
          "type": "Asset freeze|Trust Services Sanctions|Director Disqualification Sanction",
          "date": "2022-02-25"
        }
      ],
      "severity": "CRITICAL"
    }
  ],
  "donation_matches": [],
  "total_matches": 1,
  "summary": "⚠️ CRITICAL: Found 1 match(es) on UK Sanctions List. REJECT TENANT APPLICATION."
}
```

#### Risk Levels

| Risk Level | Meaning | Action |
|------------|---------|--------|
| `clear` | Not found in either database | ✅ Accept |
| `low` | Found in donations only (1-10 records) | ℹ️ Review (usually OK) |
| `medium` | Multiple donation records (>10) | ⚠️ Review recommended |
| `high` | Found in UK Sanctions List | 🚫 **REJECT** |

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `query` | string | The name you searched for |
| `screening_date` | datetime | When the check was performed (UTC) |
| `risk_level` | string | `clear`, `low`, `medium`, or `high` |
| `sanctions_matches` | array | Matches from UK Sanctions List |
| `donation_matches` | array | Matches from Electoral Commission |
| `total_matches` | integer | Total matches across both databases |
| `summary` | string | Human-readable result |

---

## Integration Example (JavaScript/TypeScript)

### Basic Integration

```javascript
async function checkSanctions(name) {
  const url = `https://sanlist-production.up.railway.app/api/screen-tenant?name=${encodeURIComponent(name)}`;

  const response = await fetch(url);
  const result = await response.json();

  return result;
}

// Usage
const result = await checkSanctions("John Smith");

if (result.risk_level === "high") {
  console.log("🚫 REJECT: Person is sanctioned");
  console.log(result.summary);
} else if (result.risk_level === "clear") {
  console.log("✅ CLEAR: No sanctions found");
} else {
  console.log("⚠️ REVIEW:", result.summary);
}
```

### Advanced Integration with Error Handling

```typescript
interface ScreeningResult {
  query: string;
  screening_date: string;
  risk_level: "clear" | "low" | "medium" | "high";
  sanctions_matches: Array<any>;
  donation_matches: Array<any>;
  total_matches: number;
  summary: string;
}

async function screenTenant(
  name: string,
  dateOfBirth?: string,
  postcode?: string
): Promise<ScreeningResult> {
  const params = new URLSearchParams({
    name,
    exact_match: "false"
  });

  if (dateOfBirth) params.append("date_of_birth", dateOfBirth);
  if (postcode) params.append("postcode", postcode);

  const url = `https://sanlist-production.up.railway.app/api/screen-tenant?${params}`;

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json"
      },
      timeout: 5000 // 5 second timeout
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return await response.json();

  } catch (error) {
    console.error("Sanctions check failed:", error);

    // Fail-safe: If API is down, log error but don't block tenant
    // (Adjust based on your risk tolerance)
    return {
      query: name,
      screening_date: new Date().toISOString(),
      risk_level: "clear", // Or throw error to block tenant
      sanctions_matches: [],
      donation_matches: [],
      total_matches: 0,
      summary: "API unavailable - manual review required"
    };
  }
}

// Usage in your tenant application flow
async function processTenantApplication(tenantData) {
  const screening = await screenTenant(
    tenantData.fullName,
    tenantData.dateOfBirth,
    tenantData.postcode
  );

  // Critical decision point
  if (screening.risk_level === "high") {
    // Automatically reject
    return {
      status: "rejected",
      reason: "Failed sanctions screening",
      details: screening.summary,
      matches: screening.sanctions_matches
    };
  }

  // For low/medium, flag for manual review
  if (screening.risk_level === "medium") {
    return {
      status: "pending_review",
      reason: "Multiple political donation records found",
      details: screening.summary,
      matches: screening.donation_matches
    };
  }

  // Clear - proceed
  return {
    status: "approved",
    screening_passed: true
  };
}
```

---

## Alternative Endpoints

### 1. Simple Name Search

**Endpoint**: `GET /api/entities`

**Best for**: Quick sanctions-only check

```bash
curl "https://sanlist-production.up.railway.app/api/entities?name=Putin&exact=false&limit=10"
```

**Parameters**:
- `name` (required): Name to search
- `exact` (optional): `true` or `false` (default: `false`)
- `limit` (optional): Max results (default: 10000)

**Response**:
```json
{
  "query": "Putin",
  "count": 3,
  "results": [
    {
      "id": 2811,
      "unique_id": "RUS0251",
      "entity_type": "Individual",
      "name": "PUTIN",
      "title": "",
      "date_of_birth": "1952-10-07T00:00:00",
      "place_of_birth": "St Petersburg (then Leningrad)",
      "nationality": "Russia",
      "passport_number": "",
      "national_id": "",
      "date_listed": "2022-02-25T00:00:00",
      "last_updated": "2025-10-26T08:09:45.919323",
      "aliases": [],
      "addresses": [
        {
          "address_line1": "",
          "address_line2": "",
          "address_line3": "",
          "city": null,
          "country": "Russia",
          "postal_code": "",
          "full_address": "Moscow"
        }
      ],
      "sanctions": [
        {
          "regime_name": "The Russia (Sanctions) (EU Exit) Regulations 2019",
          "regime_type": "Asset freeze|Trust Services Sanctions|Director Disqualification Sanction",
          "date_imposed": "2022-02-25T00:00:00"
        }
      ]
    }
  ]
}
```

### 2. Full-Text Search

**Endpoint**: `GET /api/search`

**Best for**: Complex queries (searches names, aliases, addresses)

```bash
curl "https://sanlist-production.up.railway.app/api/search?q=Russia%20Moscow&limit=10"
```

**Parameters**:
- `q` (required): Search query
- `limit` (optional): Max results (default: 10000)

### 3. Get Specific Entity

**Endpoint**: `GET /api/entity/{unique_id}`

**Best for**: Looking up a known sanctioned entity

```bash
curl "https://sanlist-production.up.railway.app/api/entity/RUS0251"
```

---

## Database Statistics

### Check System Status

**Endpoint**: `GET /api/stats`

```bash
curl "https://sanlist-production.up.railway.app/api/stats"
```

**Response**:
```json
{
  "total_entities": 5656,
  "individuals": 3820,
  "organizations": 1836,
  "total_aliases": 3828,
  "last_update": "2025-10-26T08:26:25.521802"
}
```

**Endpoint**: `GET /api/ec/stats`

```bash
curl "https://sanlist-production.up.railway.app/api/ec/stats"
```

**Response**:
```json
{
  "total_donations": 89358,
  "total_value": 1589081648.31,
  "unique_donors": 23430,
  "unique_recipients": 1672,
  "last_update": "2025-10-26T08:15:14.418455"
}
```

### Health Check

**Endpoint**: `GET /health`

```bash
curl "https://sanlist-production.up.railway.app/health"
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-29T17:00:00.000000"
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| `200` | Success | Process response |
| `404` | Entity not found | Handle as "not sanctioned" |
| `500` | Server error | Retry or fail-safe |

### Example Error Response

```json
{
  "detail": "Database connection failed"
}
```

### Recommended Error Handling Strategy

```javascript
async function safeScreening(name) {
  try {
    const response = await fetch(
      `https://sanlist-production.up.railway.app/api/screen-tenant?name=${encodeURIComponent(name)}`,
      { timeout: 5000 }
    );

    if (response.status === 500) {
      // API is down - decide your fail-safe behavior
      // Option 1: Fail open (allow tenant, log for manual review)
      console.error("Sanctions API down - manual review required");
      return { risk_level: "clear", manual_review_required: true };

      // Option 2: Fail closed (reject tenant)
      // throw new Error("Sanctions check unavailable");
    }

    return await response.json();

  } catch (error) {
    console.error("Sanctions check failed:", error);
    // Implement your fail-safe policy here
    throw error;
  }
}
```

---

## Data Freshness

- **UK Sanctions List**: Updated daily at 2 AM UTC (~5 minutes)
- **Electoral Commission**: Updated daily at 2 AM UTC (~78 seconds)
- **Total Update Time**: ~6-7 minutes per day

The API always returns the most recent data. Updates happen automatically in the background.

---

## Performance

- **Average Response Time**: ~480ms
- **Concurrent Requests**: Supports multiple simultaneous requests
- **Throughput**: ~2 requests/second (single instance), ~8 requests/second (4 workers)
- **Database**: PostgreSQL with full-text search indexes

---

## Interactive Documentation

### Web Search Interface

A public web-based search interface is available for manual searches:

**URL**: `https://sanlist-production.up.railway.app/static/index.html`

Features:
- Simple search box for names, aliases, or IDs
- Real-time search results
- Detailed entity information (sanctions, aliases, addresses)
- Database statistics
- Mobile-friendly design

Perfect for manual lookups or sharing with non-technical users.

### API Documentation (Swagger UI)

Full interactive API documentation is available at:

**URL**: `https://sanlist-production.up.railway.app/docs`

This provides:
- All endpoints with descriptions
- Try-it-out functionality
- Request/response schemas
- Example requests
- Test API calls directly from your browser

---

## Security Considerations

1. **No Authentication Required** (currently)
   - If needed, add API keys via headers: `Authorization: Bearer YOUR_API_KEY`

2. **Rate Limiting** (not currently implemented)
   - Consider adding if API is abused

3. **CORS Enabled**
   - API accepts requests from any origin
   - Adjust in production if needed

4. **HTTPS Recommended**
   - Use Railway's HTTPS endpoint in production

---

## Support & Documentation

- **Full Codebase Documentation**: See `CLAUDE.md` in the repository
- **Technical Details**: See `IMPLEMENTATION_SUMMARY.md`
- **API Swagger Docs**: `https://sanlist-production.up.railway.app/docs`

---

## Example: Complete Tenant Screening Flow

```javascript
// 1. User submits tenant application
async function handleTenantApplication(formData) {
  const { firstName, lastName, dateOfBirth, postcode } = formData;
  const fullName = `${firstName} ${lastName}`;

  // 2. Screen against sanctions and donations
  const screening = await fetch(
    `https://sanlist-production.up.railway.app/api/screen-tenant?` +
    `name=${encodeURIComponent(fullName)}&` +
    `date_of_birth=${dateOfBirth}&` +
    `postcode=${postcode}`
  ).then(r => r.json());

  // 3. Make decision based on risk level
  switch (screening.risk_level) {
    case "high":
      return {
        approved: false,
        reason: "Failed sanctions screening",
        message: "This tenant appears on the UK Sanctions List and cannot be accepted.",
        details: screening.sanctions_matches
      };

    case "medium":
      return {
        approved: false,
        reason: "Manual review required",
        message: "Multiple political donation records found. Please review manually.",
        details: screening.donation_matches
      };

    case "low":
      // Proceed but flag for records
      console.log("Info: Tenant has made political donations", screening.donation_matches);
      return {
        approved: true,
        notes: "Minor political donations found - not a concern"
      };

    case "clear":
      return {
        approved: true,
        message: "Background check passed"
      };
  }
}
```

---

## Quick Reference

**Most Common Use Case:**
```javascript
// Check if someone is sanctioned
const response = await fetch(
  `https://sanlist-production.up.railway.app/api/screen-tenant?name=John%20Smith`
);
const { risk_level, summary } = await response.json();

if (risk_level === "high") {
  console.log("REJECT:", summary);
} else {
  console.log("ACCEPT");
}
```

**Response Time**: ~480ms
**Update Frequency**: Daily at 2 AM UTC
**Sanctioned Entities**: 5,656
**Political Donations**: 89,358
**Total Value Tracked**: £1.59 billion
