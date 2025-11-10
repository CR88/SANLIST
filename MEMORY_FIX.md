# Memory Issue Fix - Nov 9, 2025

## Problem Identified

The sanctions list was not updating after Nov 7, 2025 despite:
- XML file successfully downloading (19,324,496 bytes on Nov 7)
- Parser starting ("Loading XML file" logged)
- **No completion or error messages**

## Root Cause

**Memory overlap between two scheduled updates:**

- **Sanctions Update**: Scheduled at 02:00 UTC, takes 30-40 minutes
- **Electoral Commission Update**: Was scheduled at 02:30 UTC (only 30 minutes later)

When the Nov 7 update increased the XML file size by 5KB:
1. Sanctions parser loads 19MB XML into memory at 02:00
2. EC update starts at 02:30 **while sanctions is still parsing/upserting**
3. Both processes competing for memory → Railway kills process due to OOM
4. No error logs because it's a hard kill (SIGKILL)

## Solution

Changed schedule spacing from **30 minutes** to **6 hours** in [start.py](start.py):

```python
# Before: 30 minutes apart
ec_hour = (Config.UPDATE_SCHEDULE_HOUR + 1) % 24 if Config.UPDATE_SCHEDULE_MINUTE >= 30 else Config.UPDATE_SCHEDULE_HOUR
ec_minute = (Config.UPDATE_SCHEDULE_MINUTE + 30) % 60

# After: 6 hours apart
ec_hour = (Config.UPDATE_SCHEDULE_HOUR + 6) % 24
ec_minute = Config.UPDATE_SCHEDULE_MINUTE
```

## New Schedule

- **Sanctions Update**: 02:00 UTC (30-40 minutes duration)
- **Electoral Commission Update**: 08:00 UTC (78 seconds duration)

This ensures sanctions update completes fully before EC update begins, preventing memory overlap.

## Deployment

Changes pushed to GitHub and will deploy automatically to Railway.

Next sanctions update will run at **02:00 UTC on Nov 10, 2025** with the new spacing in effect.

## Verification - Nov 10, 2025 Update

**Status: PARTIALLY SUCCESSFUL** ✅ Memory fix worked, but revealed a bug

Railway logs from Nov 10, 02:00 UTC show:
1. ✅ Parser completed successfully (5,660 entities)
2. ✅ Database upsert processed all 5,657 updates
3. ✅ No memory/OOM issues - 6-hour spacing worked!
4. ❌ Bug at final step: `NameError: name 'existing_ids' is not defined`

## Additional Bug Fix

Found and fixed bug in [src/database.py:269](src/database.py#L269):
- Variable `existing_entities` (dict) was created at line 209
- Line 269 tried to use `existing_ids` (set) which didn't exist
- Fixed by extracting keys: `existing_ids = set(existing_entities.keys())`

This bug prevented removal of delisted entities. Now fixed and deployed.

## Next Update

Nov 11, 02:00 UTC will be the first **fully successful** update with:
- ✅ 6-hour schedule spacing (no memory issues)
- ✅ Bug fix applied (delisted entities will be removed)

## Credits

Memory issue identified by user observation that updates were scheduled too close together.
