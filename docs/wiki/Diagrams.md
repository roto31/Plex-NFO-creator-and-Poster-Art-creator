# Process Flow Diagrams

All diagrams are in [Mermaid](https://mermaid.js.org/) format and render natively on GitHub.

---

## 1. Overall Pipeline — End to End

```mermaid
flowchart TD
    A([Start]) --> B[Run rename_movies.py\ndry run]
    B --> C{Review output\nlooks correct?}
    C -- No --> D[Adjust folder names\nmanually]
    D --> B
    C -- Yes --> E[Run rename_movies.py\n--rename]
    E --> F[Run scraper.py movies\n--force]
    F --> G[Run scraper.py tvshows\n--force]
    G --> H[Run extract_artwork.py movies\n--extract]
    H --> I[Run extract_artwork.py tvshows\n--extract]
    I --> J[Set Plex agent:\nLocal Media Assets → TOP]
    J --> K[Plex: Refresh All Metadata\nMovies library]
    K --> L[Plex: Refresh All Metadata\nTV Shows library]
    L --> M([Done])
```

---

## 2. scraper.py — Top-Level Flow

```mermaid
flowchart TD
    A([Start]) --> B{Mode?}
    B -- movies --> C[Scan movie root dir]
    B -- tvshows --> D[TVDB Login\nget JWT token]
    D --> E[Scan TV Shows root dir]

    C --> F[Sort folders A–Z]
    E --> G[Sort shows A–Z]

    F --> H[ThreadPoolExecutor\n4 workers]
    G --> I[ThreadPoolExecutor\n4 workers]

    H --> J[_process_one_movie\nper folder]
    I --> K[_process_one_show\nper show]

    J --> L[Aggregate results\ndone / errors / skipped]
    K --> L

    L --> M[Print summary]
    M --> N([End])
```

---

## 3. scraper.py — Movie Processing (per folder)

```mermaid
flowchart TD
    A([Folder: movie_name]) --> B{is_multipart?}
    B -- Yes --> C[⏭ Skip\nmulti-part]
    B -- No --> D{Movie.nfo exists\nAND not --force?}
    D -- Yes --> E[⏭ Skip\nalready done]
    D -- No --> F{Has video file?}
    F -- No --> G[⏭ Skip silently\nno video]
    F -- Yes --> H[clean_title\nfolder_name]
    H --> I[extract_year\nfolder_name]
    I --> J[tmdb_search\ntitle + year]
    J --> K{Result found?}
    K -- No --> L{More fuzzy\nvariants?}
    L -- Yes --> M[Try next variant\nstrip punct / accents\nremove article / subtitle]
    M --> J
    L -- No --> N[❌ Not found]
    K -- Yes --> O[tmdb_details\nid + credits + external_ids]
    O --> P[build_movie_nfo\nXML with uniqueid tags]
    P --> Q[write_nfo\nMovie.nfo]
    Q --> R[✓ Done]
```

---

## 4. scraper.py — TV Show Processing (per show)

```mermaid
flowchart TD
    A([Show folder]) --> B{tvshow.nfo exists\nAND not --force?}
    B -- Yes --> C[Read TVDB ID\nfrom uniqueid tag]
    C --> D{ID found?}
    D -- Yes --> E[_process_seasons\nskip existing NFOs]
    D -- No --> F[⏭ Skip\nno ID to resume with]
    B -- No --> G[clean_title\nshow_name]
    G --> H[tvdb_search\nwith fuzzy variants]
    H --> I{Found?}
    I -- No --> J[❌ Not found]
    I -- Yes --> K[tvdb_series_extended\nget full series data]
    K --> L[build_tvshow_nfo\nwith TVDB + TMDB + IMDb IDs]
    L --> M[write_nfo\ntvshow.nfo]
    M --> N[_process_seasons\nall season dirs]
    E --> N
    N --> O([End show])
```

---

## 5. scraper.py — Season & Episode Processing

```mermaid
flowchart TD
    A([Season dir]) --> B{Specials?}
    B -- Yes --> C[season_num = 0]
    B -- No --> D[Parse digit\nfrom dir name]
    C --> E{season.nfo exists\nAND not --force?}
    D --> E
    E -- No --> F[build_season_nfo\nwrite season.nfo]
    E -- Yes --> G[Skip season.nfo]
    F --> H[tvdb_episodes\nfetch all eps for season]
    G --> H
    H --> I[Build ep_map\nkeyed by season+episode number]
    I --> J[List video files\nin season dir]
    J --> K{More videos?}
    K -- No --> L([Done with season])
    K -- Yes --> M[Parse S##E## from filename]
    M --> N{ep_nfo exists\nAND not --force?}
    N -- Yes --> K
    N -- No --> O{S/E found\nin ep_map?}
    O -- No --> P[❌ Not found in TVDB]
    P --> K
    O -- Yes --> Q[build_episode_nfo\nwith TVDB ep ID + IMDb]
    Q --> R[write_nfo\nepisode.nfo]
    R --> K
```

---

## 6. scraper.py — Fuzzy Title Matching

```mermaid
flowchart LR
    A([Title]) --> B[Pass 1:\nClean title + year]
    B --> C{Hit?}
    C -- Yes --> Z([Return ID])
    C -- No --> D[Pass 2:\nClean title, no year]
    D --> E{Hit?}
    E -- Yes --> Z
    E -- No --> F[Pass 3:\nStrip punctuation]
    F --> G{Hit?}
    G -- Yes --> Z
    G -- No --> H[Pass 4:\nRemove leading article\nThe / A / An]
    H --> I{Hit?}
    I -- Yes --> Z
    I -- No --> J[Pass 5:\nMove trailing article\n', The' → 'The ...']
    J --> K{Hit?}
    K -- Yes --> Z
    K -- No --> L[Pass 6:\nStrip subtitle\nafter ' - ' or ': ']
    L --> M{Hit?}
    M -- Yes --> Z
    M -- No --> N[Pass 7:\nASCII-fold accents\nAmélie→Amelie]
    N --> O{Hit?}
    O -- Yes --> Z
    O -- No --> P[Pass 8:\nPunct strip + ASCII fold]
    P --> Q{Hit?}
    Q -- Yes --> Z
    Q -- No --> R([❌ Not found])
```

---

## 7. extract_artwork.py — Movie Mode Flow

```mermaid
flowchart TD
    A([Start]) --> B{ffmpeg installed?}
    B -- No --> C[❌ Print install\ninstructions & exit]
    B -- Yes --> D[Scan movie folders]
    D --> E{More folders?}
    E -- No --> F[Print summary]
    F --> G([End])
    E -- Yes --> H{is_multipart?}
    H -- Yes --> I[⏭ Skip]
    I --> E
    H -- No --> J{poster.jpg exists\nAND not --force?}
    J -- Yes --> K[⏭ Already exists]
    K --> E
    J -- No --> L[Find video file]
    L --> M{Video found?}
    M -- No --> I
    M -- Yes --> N{--extract flag?}
    N -- No --> O[Dry run:\nprobe artwork presence]
    O --> E
    N -- Yes --> P[Strategy 1:\nffmpeg -map 0:v:1]
    P --> Q{Success?\nfile > 1KB?}
    Q -- Yes --> R[✓ poster.jpg saved]
    R --> E
    Q -- No --> S[Strategy 2:\nffmpeg attached_pic]
    S --> T{Success?}
    T -- Yes --> R
    T -- No --> U[❌ No embedded artwork]
    U --> E
```

---

## 8. extract_artwork.py — TV Show Mode Flow

```mermaid
flowchart TD
    A([Show folder]) --> B[Find season dirs]
    B --> C{poster.jpg exists\nfor show?}
    C -- No --> D[Find first episode\nacross all seasons]
    D --> E[Extract → show/poster.jpg]
    C -- Yes --> F[Skip show poster]
    E --> G[For each season dir]
    F --> G
    G --> H{season/poster.jpg\nexists?}
    H -- No --> I[Extract from\nfirst episode of season]
    I --> J[→ season/poster.jpg]
    H -- Yes --> K[Skip season poster]
    J --> L[For each video file\nin season]
    K --> L
    L --> M{stem-thumb.jpg\nexists?}
    M -- Yes --> N{More videos?}
    M -- No --> O[Extract from\nthe episode video]
    O --> P[→ stem-thumb.jpg]
    P --> N
    N -- Yes --> L
    N -- No --> Q{More seasons?}
    Q -- Yes --> G
    Q -- No --> R([Done with show])
```

---

## 9. rename_movies.py — Decision Flow

```mermaid
flowchart TD
    A([Folder]) --> B{is_multipart?}
    B -- Yes --> C[⏭ Skip entirely]
    B -- No --> D[clean_name\nfolder_name]
    D --> E{Name changed?}
    E -- No --> F[Count as unchanged]
    E -- Yes --> G[For each file in folder]
    G --> H[clean_name\nfile_name]
    H --> I{File name changed?}
    I -- Yes --> J[Add to rename list]
    I -- No --> G
    J --> K[Print FOLDER header]
    K --> L{--rename flag?}
    L -- No --> M[Print WOULD RENAME]
    L -- Yes --> N[os.rename files\nfirst]
    N --> O[os.rename folder]
    M --> P([Next folder])
    O --> P
    F --> P
```

---

## 10. clean_title() — Transformation Pipeline

```mermaid
flowchart LR
    A([Raw folder name]) --> B[Strip leading\n1-2 digit prefix\nif followed by letter]
    B --> C[Strip trailing\nyear in parens]
    C --> D[Strip quality tags\nin brackets/parens\n1080p BluRay WEB-DL etc]
    D --> E[Strip remaining\nbracket content]
    E --> F[Strip trailing\n_ - . spaces]
    F --> G[Replace _ with space]
    G --> H[Collapse\ndouble spaces]
    H --> I([Clean title])
```

---

## 11. Plex Configuration After Running Scripts

```mermaid
flowchart TD
    A([Scripts complete]) --> B[Open Plex Web UI\nlocalhost:32400/web]
    B --> C[Settings → Libraries]
    C --> D[Movies library → Edit]
    D --> E[Agents tab]
    E --> F[Drag 'Local Media Assets'\nto TOP of list]
    F --> G[Save]
    G --> H[TV Shows library → Edit]
    H --> I[Same: Local Media Assets\nto TOP]
    I --> J[Save]
    J --> K[Movies → ⋯ →\nManage Library →\nRefresh All Metadata]
    K --> L[TV Shows → ⋯ →\nManage Library →\nRefresh All Metadata]
    L --> M[Wait 10–30 min\nfor Plex to re-index]
    M --> N([Metadata & artwork\nnow showing in Plex])
```
