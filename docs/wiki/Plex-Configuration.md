# Plex Configuration

After running the scripts, Plex needs to be configured to read your new `.nfo` files and `poster.jpg` sidecars. This requires two things: setting the right agent priority and triggering a metadata refresh.

---

## Step 1 — Set Local Media Assets as Top Agent

### Movies Library

1. Open Plex at `http://localhost:32400/web`
2. Go to **Settings** (wrench icon) → **Libraries**
3. Find your Movies library, click the **pencil/edit** icon
4. Click the **Agents** tab at the top
5. Find **Local Media Assets (Movies)** in the agent list
6. Drag it to the **very top** of the priority list
7. Click **Save Changes**

### TV Shows Library

Repeat the same steps for your TV Shows library, placing **Local Media Assets (TV)** at the top.

> **Why this matters:** If Local Media Assets is not first in the list, Plex will use its online agents (Plex Movie, The Movie Database, TheTVDB) and ignore your `.nfo` files entirely. The agent priority order is not a suggestion — Plex uses the **first** agent that can match each item.

---

## Step 2 — Refresh All Metadata

After saving the agent configuration:

### Movies

1. In your Plex library list, hover over the Movies library
2. Click the **three dots** (`⋯`) menu
3. Choose **Manage Library** → **Refresh All Metadata**
4. Click **Refresh All Metadata** to confirm

### TV Shows

Repeat for the TV Shows library.

Plex will begin scanning all items. On a large library (1,700+ movies, 300+ shows), this can take **15–45 minutes**. You can monitor progress in **Settings → Troubleshooting → Logs** or by watching the library update in the Plex UI.

---

## Step 3 — Fix Any Remaining Mismatches Manually

After the refresh, some items may still be wrong — typically:
- Home recordings or local content not in TMDB/TVDB (no NFO exists)
- Items where the NFO was generated but contains an incorrect match

For these, use **Fix Incorrect Match** in Plex:
1. Click the three dots on the title
2. Choose **Fix Incorrect Match**
3. Search for the correct title and select it

This manually pins the match in Plex's database and will survive future refreshes.

---

## Verifying the Configuration Worked

After the refresh completes, check a few items:

1. Open a movie detail page in Plex
2. Click the **three dots** → **Get Info**
3. The **Metadata Source** field should show **Local Media Assets**

If it still shows "The Movie Database" or another agent, the Local Media Assets agent is not at the top of the priority list. Double-check the agent order in Settings → Libraries.

---

## Keeping Metadata in Sync

After adding new movies or TV episodes:

1. Run `scraper.py` for the new items (it will skip existing NFOs)
2. Run `extract_artwork.py` for the new items (same skip logic)
3. In Plex: **Manage Library → Scan Library Files** (not "Refresh All Metadata" — scanning is faster and only processes new files)

Plex will detect the new `.nfo` files and pick up the metadata automatically.

---

## Common Configuration Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Local Media Assets not at top | NFOs ignored; wrong metadata from online agents | Move LMA to top of agent list |
| Refreshed before setting agent | LMA is at top but metadata still wrong | Run "Refresh All Metadata" again |
| Library path changed | Plex can't find the files | Edit library and update the folder path |
| NFO files not readable by Plex | Metadata shows as unknown | Check file permissions: `chmod 644 Movie.nfo` |
| `poster.jpg` not showing | Still shows old/generic poster | Force-refresh that specific item via its three-dots menu |

---

## Agent Priority Explained

Plex agent priority works like this: for each item, Plex goes down the agent list from top to bottom and uses the **first agent that returns a match**. If Local Media Assets is at the top and a `.nfo` file is present, Plex uses the NFO and never consults the online agents.

This means:
- Items **with** NFO files → metadata from NFO (fast, accurate, offline)
- Items **without** NFO files → Plex falls through to the next agent in the list

The online agents (Plex Movie, TMDB, TVDB) remain in the list as fallbacks for items you don't have NFO files for. This is the correct configuration — Local Media Assets at the top, online agents below.
