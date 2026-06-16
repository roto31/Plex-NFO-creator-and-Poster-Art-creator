# NFO Format Reference

Plex reads `.nfo` files through its **Local Media Assets** agent. The format follows the Kodi XML schema with Plex-specific extensions for `<uniqueid>` tags.

---

## Movie.nfo

**Filename:** `Movie.nfo` (case-insensitive on macOS)
**Location:** Same folder as the video file

```xml
<?xml version='1.0' encoding='utf-8'?>
<movie>
  <!-- Title as it appears in Plex -->
  <title>Back to the Future</title>

  <!-- Database IDs — Plex uses these to pin the exact match -->
  <!-- default="true" marks the primary source -->
  <uniqueid type="tmdb" default="true">105</uniqueid>
  <uniqueid type="imdb" default="false">tt0088763</uniqueid>

  <!-- Release year -->
  <year>1985</year>

  <!-- Full plot synopsis -->
  <plot>Marty McFly is accidentally sent back in time to 1955, where he must ensure
  his parents meet and fall in love, and find a way to return to 1985.</plot>

  <!-- Runtime in minutes -->
  <runtime>116</runtime>

  <!-- TMDB vote average (0.0–10.0) -->
  <rating>8.5</rating>

  <!-- Content rating (requires separate API call — left blank in current version) -->
  <!-- <mpaa>PG</mpaa> -->

  <!-- One <genre> tag per genre -->
  <genre>Adventure</genre>
  <genre>Comedy</genre>
  <genre>Science Fiction</genre>

  <!-- Primary production company -->
  <studio>Universal Pictures</studio>

  <!-- One <director> tag per director -->
  <director>Robert Zemeckis</director>

  <!-- Up to 10 cast members -->
  <actor>
    <name>Michael J. Fox</name>
    <role>Marty McFly</role>
  </actor>
  <actor>
    <name>Christopher Lloyd</name>
    <role>Dr. Emmett Brown</role>
  </actor>
  <actor>
    <name>Lea Thompson</name>
    <role>Lorraine Baines</role>
  </actor>
</movie>
```

---

## tvshow.nfo

**Filename:** `tvshow.nfo`
**Location:** Show root folder (e.g. `Breaking Bad/tvshow.nfo`)

```xml
<?xml version='1.0' encoding='utf-8'?>
<tvshow>
  <title>Breaking Bad</title>

  <!-- TVDB is primary for TV shows; TMDB and IMDb are supplementary -->
  <uniqueid type="tvdb" default="true">81189</uniqueid>
  <uniqueid type="tmdb" default="false">1396</uniqueid>
  <uniqueid type="imdb" default="false">tt0903747</uniqueid>

  <year>2008</year>
  <plot>A high school chemistry teacher diagnosed with inoperable lung cancer
  turns to manufacturing and selling methamphetamine with a former student
  in order to secure his family's future.</plot>

  <!-- Average episode runtime in minutes -->
  <runtime>47</runtime>

  <rating>9.5</rating>

  <genre>Drama</genre>
  <genre>Crime</genre>
  <genre>Thriller</genre>

  <!-- Broadcast network -->
  <network>AMC</network>

  <actor>
    <name>Bryan Cranston</name>
    <role>Walter White</role>
  </actor>
  <actor>
    <name>Aaron Paul</name>
    <role>Jesse Pinkman</role>
  </actor>
</tvshow>
```

---

## season.nfo

**Filename:** `season.nfo`
**Location:** Season folder (e.g. `Breaking Bad/Season 1/season.nfo`)

```xml
<?xml version='1.0' encoding='utf-8'?>
<season>
  <title>Season 1</title>
  <season>1</season>
</season>
```

For Specials (Season 0):

```xml
<?xml version='1.0' encoding='utf-8'?>
<season>
  <title>Specials</title>
  <season>0</season>
</season>
```

---

## Episode .nfo

**Filename:** Same as video file, `.nfo` extension
**Example:** `Breaking Bad - S01E01.nfo` alongside `Breaking Bad - S01E01.mp4`
**Location:** Season folder

```xml
<?xml version='1.0' encoding='utf-8'?>
<episodedetails>
  <title>Pilot</title>
  <season>1</season>
  <episode>1</episode>

  <!-- TVDB episode ID is primary; IMDb episode ID when available -->
  <uniqueid type="tvdb" default="true">349232</uniqueid>
  <uniqueid type="imdb" default="false">tt0959621</uniqueid>

  <plot>Walter White, a chemistry teacher, is diagnosed with inoperable lung cancer
  and turns to a life of crime, producing and selling methamphetamine with his
  former student Jesse Pinkman.</plot>

  <!-- TVDB episode rating -->
  <rating>9.0</rating>

  <!-- Original air date -->
  <aired>2008-01-20</aired>

  <!-- Episode runtime in minutes -->
  <runtime>58</runtime>

  <director>Vince Gilligan</director>

  <actor>
    <name>Bryan Cranston</name>
    <role>Walter White</role>
  </actor>
</episodedetails>
```

---

## The `<uniqueid>` Tag

This is the most important tag for reliable Plex matching.

```xml
<uniqueid type="tmdb" default="true">105</uniqueid>
```

| Attribute | Values | Description |
|-----------|--------|-------------|
| `type` | `tmdb`, `tvdb`, `imdb` | Which database this ID belongs to |
| `default` | `true` or `false` | Marks the primary/authoritative source |

**Rules:**
- Only ONE `<uniqueid>` per item should have `default="true"`
- For movies: `tmdb` is default (we scrape from TMDB)
- For TV shows/episodes: `tvdb` is default (we scrape from TVDB)
- IMDb IDs always have `default="false"` — they are supplementary

Without `<uniqueid>` tags, Plex must match by title alone, which is unreliable for remakes, films with similar titles, and items with non-standard folder names.

---

## Artwork Sidecar Files

| Filename | What Plex Uses It For |
|----------|-----------------------|
| `poster.jpg` in movie folder | Movie poster |
| `poster.jpg` in show folder | TV show poster |
| `poster.jpg` in season folder | Season poster |
| `{episode-filename}-thumb.jpg` | Episode thumbnail |

All artwork files must be JPEG. PNG is also supported but JPEG is preferred.

---

## Field Sources

### Movies (from TMDB)

| NFO Field | TMDB API Field |
|-----------|---------------|
| `<title>` | `title` |
| `<uniqueid type="tmdb">` | `id` |
| `<uniqueid type="imdb">` | `external_ids.imdb_id` |
| `<year>` | `release_date[:4]` |
| `<plot>` | `overview` |
| `<runtime>` | `runtime` |
| `<rating>` | `vote_average` |
| `<genre>` | `genres[].name` |
| `<studio>` | `production_companies[0].name` |
| `<director>` | `credits.crew` (job == "Director") |
| `<actor>` | `credits.cast[:10]` |

### TV Shows (from TVDB)

| NFO Field | TVDB API Field |
|-----------|---------------|
| `<title>` | `name` |
| `<uniqueid type="tvdb">` | `id` |
| `<uniqueid type="tmdb">` | `remoteIds[].id` (sourceName contains "MovieDB") |
| `<uniqueid type="imdb">` | `remoteIds[].id` (sourceName contains "IMDB") |
| `<year>` | `firstAired[:4]` |
| `<plot>` | `overview` |
| `<runtime>` | `averageRuntime` |
| `<rating>` | `score` |
| `<genre>` | `genres[].name` |
| `<network>` | `networks[0].name` |
| `<actor>` | `characters[]` (type==1 or peopleType=="Actor") |

### Episodes (from TVDB)

| NFO Field | TVDB API Field |
|-----------|---------------|
| `<title>` | `name` |
| `<season>` | `seasonNumber` |
| `<episode>` | `number` |
| `<uniqueid type="tvdb">` | `id` |
| `<uniqueid type="imdb">` | `remoteIds[].id` (sourceName contains "IMDB") |
| `<plot>` | `overview` |
| `<rating>` | `score` or `siteRating` |
| `<aired>` | `aired` |
| `<runtime>` | `runtime` |
| `<director>` | `directors[].name` |
