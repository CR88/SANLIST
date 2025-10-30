# Railway Database Connection Fix

## Problem

Railway is not setting the `DATABASE_URL` environment variable, causing the app to try connecting to `localhost` instead of the Railway PostgreSQL database.

## Solution

### Step 1: Add PostgreSQL Database to Your Railway Project

1. Go to your Railway project dashboard
2. Click **"+ New"** button
3. Select **"Database"** → **"PostgreSQL"**
4. Railway will create a PostgreSQL database and automatically link it

### Step 2: Verify Environment Variables

After adding the PostgreSQL database, Railway should automatically set these variables:

**In your service (not the database service), check Variables tab:**

You should see one of these:
- `DATABASE_URL` (most common)
- `PGURL` (alternative)
- `DATABASE_PRIVATE_URL` (internal network)

**If you don't see any database variables:**

1. Click on your **service** (not the database)
2. Go to **"Settings"** tab
3. Scroll to **"Service Variables"**
4. Click **"+ New Variable"** → **"Reference"**
5. Select the PostgreSQL database
6. Choose `DATABASE_URL` from the dropdown

### Step 3: Manual Setup (If Needed)

If Railway doesn't auto-link, manually copy the connection string:

1. Click on your **PostgreSQL database service**
2. Go to **"Variables"** tab
3. Find `DATABASE_URL` or `DATABASE_PRIVATE_URL`
4. Copy the value (looks like: `postgresql://postgres:...@...railway.app/railway`)
5. Go back to your **API service**
6. Go to **"Variables"** tab
7. Add new variable:
   - Name: `DATABASE_URL`
   - Value: Paste the connection string

### Step 4: Redeploy

After adding the environment variable:

1. Go to **"Deployments"** tab
2. Click **"Deploy"** → **"Redeploy"**
3. Watch the logs for the debug message showing the database URL

### Expected Log Output (After Fix)

```
2025-10-30 08:10:00,000 - __main__ - INFO - Checking database initialization...
2025-10-30 08:10:00,001 - __main__ - INFO - Using database: postgresql://postgres:****@...railway.app:5432/railway
2025-10-30 08:10:01,000 - __main__ - INFO - ✓ UK Sanctions tables ready
2025-10-30 08:10:01,000 - __main__ - INFO - ✓ Electoral Commission tables ready
```

## Code Changes Made

I've updated the code to:

1. **Check multiple environment variable names** ([src/config.py](src/config.py)):
   - `DATABASE_URL` (standard)
   - `PGURL` (Railway alternative)
   - `DATABASE_PRIVATE_URL` (Railway internal network)

2. **Add debug logging** ([start.py](start.py)):
   - Shows which database URL is being used
   - Lists available environment variables if none found

## Quick Test

After redeploying, check logs for this line:
```
Using database: postgresql://postgres:****@...railway.app:5432/railway
```

If you still see `localhost`, the environment variable isn't set correctly.

## Alternative: Use Railway's Private Network URL

If you have issues with the public `DATABASE_URL`, try the private network URL:

1. Click PostgreSQL database → Variables
2. Copy `DATABASE_PRIVATE_URL`
3. Add it as `DATABASE_URL` in your service

Private URLs are faster and more reliable within Railway's network.

## Common Railway Database Variable Names

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Public connection string (use this) |
| `DATABASE_PRIVATE_URL` | Private network URL (faster) |
| `PGHOST` | Host only |
| `PGPORT` | Port only |
| `PGUSER` | Username only |
| `PGPASSWORD` | Password only |
| `PGDATABASE` | Database name only |

The code now checks all of these automatically.

## Still Not Working?

If you still see localhost errors:

1. **Check the PostgreSQL service is running**:
   - Railway Dashboard → PostgreSQL service → should show "Active"

2. **Verify service linking**:
   - Your API service should show a connection to PostgreSQL database
   - Look for a line connecting them in the project view

3. **Check logs for the debug output**:
```bash
railway logs
```

Look for:
```
⚠️ No DATABASE_URL environment variable found!
⚠️ Available env vars: [list of variables]
```

This will tell you which variables ARE available.

4. **Force set DATABASE_URL manually**:
   - Get connection string from PostgreSQL service Variables tab
   - Add it manually to your API service Variables tab
   - Redeploy

## Need More Help?

Share the output of these log lines and I can debug further:
```
Using database: ...
⚠️ No DATABASE_URL environment variable found!
⚠️ Available env vars: ...
```
