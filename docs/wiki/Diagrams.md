# Process & Decision Flow Diagrams

All diagrams are written in [Mermaid](https://mermaid.js.org/) and render natively on GitHub.

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

## 2. preflight.py — Startup Check Sequence

Every script runs these checks before opening the progress window.

```mermaid
flowchart TD
    A([Script launched]) --> B[setup_logging\ncreate log file]
    B --> C[check_python_version\n≥ 3.8?]
    C -- Fail --> Z1[❌ Exit: Python too old]
    C -- Pass --> D{Script needs\nAPI keys?}
    D -- Yes --> E[check_api_keys\nTMDB + TVDB set?]
    E -- Fail --> Z2[❌ Exit: keys not set]
    E -- Pass --> F{Script needs\nffmpeg?}
    D -- No --> F
    F -- Yes --> G[check_ffmpeg\nshutil.which ffmpeg]
    G -- Found --> H{Writing\nfiles?}
    G -- Not found --> I[ffmpeg missing flow\nsee Diagram 3]
    I -- Installed OK --> H
    I -- Not installed --> Z3[❌ Exit: ffmpeg required]
    F -- No --> H
    H -- Yes --> J[check_write_permission\ntest write to path]
    J -- Fail --> Z4[❌ Exit: no write access]
    J -- Pass --> K[All checks passed\nopen ProgressWindow]
    H -- No --> K
    K --> L([Begin processing])
```

---

## 3. preflight.py — ffmpeg Missing: Install Decision Flow

```mermaid
flowchart TD
    A([ffmpeg not on PATH]) --> B[OS-native notification:\nffmpeg is required]
    B --> C[OS-native dialog:\nInstall automatically?]
    C -- Yes --> D{Platform?}
    D -- macOS --> E{Homebrew\ninstalled?}
    E -- No --> F[Install Homebrew\nfrom brew.sh]
    F --> G[brew install ffmpeg]
    E -- Yes --> G
    D -- Linux --> H{Package manager?}
    H -- apt --> I[apt-get install ffmpeg]
    H -- dnf --> J[dnf install ffmpeg]
    H -- pacman --> K[pacman -S ffmpeg]
    H -- zypper --> L[zypper install ffmpeg]
    H -- brew --> G
    D -- Windows --> M{winget\navailable?}
    M -- Yes --> N[winget install ffmpeg]
    M -- No --> O[choco install ffmpeg]
    I & J & K & L & N & O --> P[Re-check PATH]
    P -- Found --> Q([✓ ffmpeg ready])
    P -- Not found --> R[Print PATH instructions\nopen download page\nin browser]
    R --> Z([❌ Exit])
    C -- No --> R
```

---

## 4. preflight.py — Progress Window Threading Model

```mermaid
sequenceDiagram
    participant Main as Main Thread
    participant Queue as queue.Queue
    participant Worker as Worker Thread
    participant UI as tkinter UI

    Main->>UI: build_ui() — create widgets
    Main->>Worker: Thread(target=work_fn).start()
    Main->>UI: root.after(100, _poll)
    Main->>UI: root.mainloop() [blocks]

    loop Every 100ms
        UI->>Queue: _poll() — drain messages
        Queue-->>UI: progress update / log line / done signal
        UI->>UI: update progress bar, counters, log
    end

    loop Per item
        Worker->>Queue: put(progress_update)
        Worker->>Queue: put(log_line)
        Worker->>Worker: check cancel() flag
    end

    Worker->>Queue: put(done_signal)
    Queue-->>UI: _poll() sees done
    UI->>UI: show final counts
    UI->>Main: root.quit()
    Main-->>Main: mainloop() returns
    Main->>Main: return (done, errors, skipped)
```

---

## 5. preflight.py — Log File Lifecycle

```mermaid
flowchart LR
    A([Script starts]) --> B[log_directory\nplatform path]
    B --> C[mkdir -p\nif not exists]
    C --> D[filename:\nscript_YYYY-MM-DD_HHMMSS.log]
    D --> E[FileHandler\n+ StreamHandler stderr]
    E --> F[Logger ready]
    F --> G{Processing\nruns}
    G --> H[All items logged\nto file + stderr]
    H --> I([Run ends])
    I --> J{Open Log\nbutton clicked?}
    J -- Yes --> K{Platform?}
    K -- macOS --> L[open -a Console.app\nlog_file]
    K -- Linux --> M[xdg-open log_file]
    K -- Windows --> N[notepad log_file]
    J -- No --> O([Log persists\nfor future reference])
```

---

## 6. scraper.py — Top-Level Flow (v1.2)

```mermaid
flowchart TD
    A([Start]) --> B[preflight checks\nPython + API keys + write perm]
    B --> C[setup_logging scraper]
    C --> D{Mode?}
    D -- movies --> E[Count movie folders]
    D -- tvshows --> F[TVDB Login\nget JWT token]
    F --> G[Count TV show folders]

    E --> H[ProgressWindow\ntitle + total + log_file]
    G --> H

    H --> I[work closure defined]
    I --> J[win.run work]

    J --> K[ThreadPoolExecutor\n4 workers + as_completed]
    K -- movies --> L[_process_one_movie\nper folder]
    K -- tvshows --> M[_process_one_show\nper show]

    L & M --> N[progress_cb per item\nupdate bar + counters]
    N --> O[log_cb per item\nwrite to window + file]
    O --> P{cancel?}
    P -- Yes --> Q[Stop submitting\nnew work]
    P -- No --> K

    K --> R[Aggregate done / errors / skipped]
    R --> S[logger.info Finished]
    S --> T[notify completion]
    T --> U([Window shows\nfinal counts])
```

---

## 7. scraper.py — Movie Processing (per folder)

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

## 8. scraper.py — TV Show Processing (per show)

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

## 9. scraper.py — Season & Episode Processing

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

## 10. scraper.py — Fuzzy Title Matching

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

## 11. extract_artwork.py — Startup Flow (v1.2)

```mermaid
flowchart TD
    A([Start]) --> B[preflight checks\nPython + ffmpeg + write perm]
    B --> C[setup_logging extract_artwork]
    C --> D[Count folders]
    D --> E[ProgressWindow\ntitle + total + log_file]
    E --> F[win.run work]
    F --> G{Mode?}
    G -- movies --> H[process_movies\nwith callbacks]
    G -- tvshows --> I[process_tvshows\nwith callbacks]
    H & I --> J[Return done / errors / skipped]
    J --> K[logger.info Finished]
    K --> L[notify completion]
    L --> M([Window shows\nfinal counts])
```

---

## 12. extract_artwork.py — Movie Mode Flow

```mermaid
flowchart TD
    A([Start]) --> D[Scan movie folders]
    D --> E{More folders?}
    E -- No --> F[Print summary]
    F --> G([End])
    E -- Yes --> CA{cancel?}
    CA -- Yes --> G
    CA -- No --> H{is_multipart?}
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
    Q -- Yes --> R[✓ poster.jpg saved\nprogress_cb done]
    R --> E
    Q -- No --> S[Strategy 2:\nffmpeg attached_pic]
    S --> T{Success?}
    T -- Yes --> R
    T -- No --> U[❌ No embedded artwork\nprogress_cb error]
    U --> E
```

---

## 13. extract_artwork.py — TV Show Mode Flow

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
    Q -- No --> R[progress_cb done\nfor this show]
    R --> S([Done with show])
```

---

## 14. rename_movies.py — Startup Flow (v1.2)

```mermaid
flowchart TD
    A([Start]) --> B[preflight checks\nPython version]
    B --> C{--rename flag?}
    C -- Yes --> D[check_write_permission]
    D -- Fail --> Z[❌ Exit]
    D -- Pass --> E[setup_logging rename_movies]
    C -- No --> E
    E --> F[Count folders]
    F --> G[ProgressWindow\ntitle + total + log_file]
    G --> H[win.run work]
    H --> I[process_movies\nwith callbacks]
    I --> J[Return done / errors / skipped]
    J --> K[notify completion]
    K --> L([Window shows\nfinal counts])
```

---

## 15. rename_movies.py — Decision Flow

```mermaid
flowchart TD
    A([Folder]) --> CA{cancel?}
    CA -- Yes --> Z([Stop])
    CA -- No --> B{is_multipart?}
    B -- Yes --> C[⏭ Skip entirely\nprogress_cb skipped]
    B -- No --> D[clean_name\nfolder_name]
    D --> E{Name changed?}
    E -- No --> F[Count as unchanged\nprogress_cb skipped]
    E -- Yes --> G[For each file in folder]
    G --> H[clean_name\nfile_name]
    H --> I{File name changed?}
    I -- Yes --> J[Add to rename list]
    I -- No --> G
    J --> K[log_cb FOLDER header]
    K --> L{--rename flag?}
    L -- No --> M[log_cb WOULD RENAME\nprogress_cb done]
    L -- Yes --> N[os.replace files\nfirst]
    N --> O[os.replace folder]
    O --> P[log_cb RENAMED\nprogress_cb done]
    M & P --> Q([Next folder])
    F --> Q
    C --> Q
```

---

## 16. clean_title() — Transformation Pipeline

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

## 17. Plex Configuration After Running Scripts

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

---

## Diagram 18 — Metadata Generator: System Architecture

```mermaid
flowchart TD
  subgraph APIs
    TVDB[TheTVDB v4]
    TMDB[TMDB v3]
    FANART[FanArt.tv v3]
    Tunarr[Tunarr SQLite]
    iTunes[iTunes Search API]
    MusicKit[Apple MusicKit\noptional]
    MB[MusicBrainz API]
  end
  subgraph Generator
    TV[process_tv_library]
    MOV[process_movie_library]
    MUS[process_music_library\nextended only]
  end
  subgraph Skip["Selective Processing"]
    CHECK{NFO exists?\nAll art exists?}
    SKIP[⏭ Skip — already complete]
    RUN[Fetch metadata\nWrite NFO\nDownload missing art]
  end
  TVDB & TMDB & Tunarr --> TV
  FANART -- clearart/logo/landscape --> TV
  TMDB --> MOV
  FANART -- clearart/disc/logo\nposter fallback --> MOV
  iTunes & MusicKit & MB --> MUS
  TV & MOV & MUS --> CHECK
  CHECK -- All present --> SKIP
  CHECK -- Missing NFO or art --> RUN
  RUN --> NFO[NFO files]
  RUN --> ART["poster.jpg · folder.jpg\nbackdrop.jpg · clearart.png\ndisc.png · logo.png"]
  NFO & ART --> Plex[Plex Local Media Assets]
```

---

## Diagram 19 — Metadata Generator: Movie Processing Flow

```mermaid
flowchart TD
  A([Scan movies_library_root]) --> B[For each folder]
  B --> C{is_multipart?}
  C -- Yes --> D[⏭ Skip — multi-part]
  C -- No --> E[_needs_movie_artwork\ncheck all 6 files]
  E --> F{Movie.nfo missing\nOR any art missing?}
  F -- Neither --> G[⏭ Skip — already complete]
  F -- Yes --> H{Movie.nfo exists?}
  H -- Yes --> I[Parse existing NFO\n_extract_tmdb_id_from_nfo\nno search API call]
  H -- No --> J[Extract year from folder name]
  J --> K[TMDbMovieProvider\nsearch_movie title + year]
  K --> L{Found?}
  L -- No with year --> M[Retry without year]
  M --> L
  L -- No --> N[❌ Not found — log error]
  I & L -- Yes --> O[get_movie details\ncredits + external_ids]
  O --> P{NFO needed?}
  P -- Yes --> Q[generate_movie_nfo → Movie.nfo]
  P -- No --> R
  Q --> R{poster or\nbackdrop needed?}
  R -- Yes --> S[Download TMDB\nposter + backdrop\ncopy → folder.jpg]
  S --> T
  R -- No --> T{clearart / disc /\nlogo needed?}
  T -- Yes --> U[FanartTvProvider\nget_movie_artwork]
  U --> V[Download only\nmissing FanArt.tv files\nclearart / disc / logo]
  V --> B
  T -- No --> B
  G & N --> B
  B --> W[refresh_plex_library\nmovies_library_key]
```

---

## Diagram 20 — Metadata Generator: TV Show Processing Flow

```mermaid
flowchart TD
  A([Scan tv_library_root]) --> B[For each show folder]
  B --> C{tvshow.nfo missing\nOR show art missing?}
  C -- Nothing missing --> D[Skip show-level — check seasons]
  C -- Missing --> E[_find_show_metadata]
  E --> F{TVDb found?}
  F -- No --> G[TMDb fallback]
  G --> H{TMDb found?}
  H -- No --> I[Tunarr fallback]
  I --> J{Found?}
  J -- No --> K[❌ Not found]
  F -- Yes --> L[get_show details\nartworks incl. banner + fanart]
  H -- Yes --> L
  J -- Yes --> L
  L --> M[generate_show_nfo → tvshow.nfo]
  M --> N[Download TVDB poster\nbanner + fanart]
  N --> O{clearart / logo /\nlandscape needed?}
  O -- Yes --> P[FanartTvProvider\nget_tv_artwork tvdb_id]
  P --> Q[Download missing\nFanArt.tv files]
  Q --> D
  O -- No --> D
  D --> R[For each Season dir]
  R --> S{season.nfo missing\nor poster.jpg missing?}
  S -- Neither --> T[Skip — check episodes]
  S -- Missing --> U[Write season.nfo\nDownload season poster from TVDB]
  U --> T
  T --> V[For each episode video]
  V --> W{episode.nfo missing\nor thumb missing?}
  W -- Neither --> X[⏭ Skip episode]
  W -- Missing --> Y[TVDb/TMDb get_episodes]
  Y --> Z[generate_episode_nfo\nDownload episode thumb]
  Z & X --> V
```

---

## Diagram 21 — Metadata Generator: Music Processing Flow

```mermaid
flowchart TD
  A([Scan music_library_root]) --> B[For each Artist dir]
  B --> C{artist.nfo missing\nor artist.jpg missing?}
  C -- Neither --> D[Skip artist-level — check albums]
  C -- Missing --> E[MusicBrainzProvider.search_artist\nlocal DB or REST]
  E --> F{Found?}
  F -- No --> G[Apple MusicKit\nif configured]
  G --> GA{Found?}
  GA -- No --> GB[iTunes search_artist]
  GA -- Yes --> J
  GB --> H{Found?}
  H -- No --> I[⚠ No artist metadata]
  F -- Yes --> J[generate_artist_nfo\nDownload artist.jpg]
  H -- Yes --> J
  J --> D
  D --> K[For each Album dir]
  K --> L{album.nfo missing\nor cover.jpg missing?}
  L -- Neither --> M[Skip album-level — check tracks]
  L -- Missing --> N[Apple MusicKit\nif configured]
  N --> O{Found?}
  O -- No --> P[iTunes search_album\n3000×3000 cover art]
  O -- Yes --> Q[generate_album_nfo\nDownload cover.jpg]
  P --> Q
  Q --> M
  M --> R[For each audio track]
  R --> S{track.nfo missing?}
  S -- No --> T[⏭ Skip track]
  S -- Yes --> U[generate_track_nfo\nMBID + ISRC from album]
  U & T --> R
```

---

## Diagram 22 — Metadata Generator: --media-type Decision Flow

```mermaid
flowchart TD
  A([Script launched]) --> B[Parse --media-type]
  B --> C{Value?}
  C -- tv --> D[process_tv_library\nTVDB + TMDB + FanArt.tv + Tunarr]
  C -- movies --> E[process_movie_library\nTMDB + FanArt.tv]
  C -- music --> F[process_music_library\niTunes + Apple MusicKit + MusicBrainz\nextended script only]
  C -- all --> G[Run all applicable\nbased on config keys present]
  G --> D & E & H{Extended\nscript?}
  H -- Yes --> F
  H -- No --> I[Skip music]
  D --> J[refresh_plex tv_library_key]
  E --> K[refresh_plex movies_library_key]
  F --> L[refresh_plex music_library_key]
```

---

## Diagram 23 — Metadata Generator: Scheduling Architecture

```mermaid
flowchart TD
  A([Daily trigger]) --> B{Platform?}
  B -- macOS --> C[LaunchAgent\ncom.plexmetadata.generator.plist\ninstall-macos.sh]
  B -- Linux --> D[systemd timer\nplex-metadata-generator.timer\ninstall-linux.sh]
  B -- Windows --> E[Task Scheduler XML\nplex-metadata-generator-windows.xml\ninstall-windows.ps1]
  B -- Any --> F[Cron\nplex-metadata-generator-cron]
  B -- Docker --> G[docker-compose.yml\nCronJob in container]
  C & D & E & F & G --> H[plex_metadata_generator.py\n--media-type all]
  H --> I{Selective check\nper item}
  I -- NFO + all art present --> J[⏭ Skip — zero API calls]
  I -- Missing NFO or art --> K[Fetch only what is needed\nWrite NFO + download art]
  K --> L[Plex API refresh]
```

---

## Diagram 24 — Extended Script: Complete System Architecture

```mermaid
flowchart TD
  subgraph Input["Library Roots (config or first-run dialog)"]
    MOV_ROOT[movies_library_roots]
    TV_ROOT[tv_library_roots]
    MUS_ROOT[music_library_roots]
  end

  subgraph MovieAPIs["Movie APIs"]
    TMDB[TMDB v3\nMovie metadata\nposter + backdrop]
    FANART_MOV[FanArt.tv v3\nclearart · disc · logo]
  end

  subgraph TVAPIS["TV APIs"]
    TVDB[TheTVDB v4\nShow + episode metadata\nseason/episode artwork]
    TMDB_TV[TMDB v3\nTV fallback]
    TUNARR[Tunarr SQLite\nChannel metadata fallback]
    FANART_TV[FanArt.tv v3\nclearart · logo · landscape]
  end

  subgraph MusicAPIs["Music APIs — priority cascade"]
    MB_DB[MusicBrainz\nLocal PostgreSQL DB\noptional · instant]
    MB_JSON[MusicBrainz\nJSON Dump\noptional · no DB needed]
    MUSICKIT[Apple MusicKit\noptional · $99/yr]
    ITUNES[iTunes Search API\nalways active · free]
    MB_REST[MusicBrainz REST\nrate-limited fallback]
  end

  subgraph SubAPIs["Subtitle APIs"]
    OPENSUB[OpenSubtitles\nprimary · 5-40/day]
    SUBDL[Subdl\nautomatic fallback]
  end

  subgraph Processing["Extended Script Processing"]
    MOV_PROC[process_movie_library\nTMDB + FanArt.tv]
    TV_PROC[process_tv_library\nTVDB + TMDB + FanArt.tv + Tunarr]
    MUS_PROC[process_music_library\nMusic provider cascade]
    SUB_PROC[SubtitleDownloader\nper video file]
  end

  subgraph Output["Written to disk"]
    NFO[NFO files\nMovie.nfo · tvshow.nfo\nalbum.nfo · artist.nfo\ntrack.nfo · episode.nfo]
    ART[Artwork\nposter · backdrop · folder\nclearart · disc · logo\nbanner · fanart · landscape\ncover · artist.jpg]
    SUBS[Subtitles\nstem.lang.srt sidecar\nmov_text embedded track]
  end

  MOV_ROOT --> MOV_PROC
  TV_ROOT  --> TV_PROC
  MUS_ROOT --> MUS_PROC

  TMDB --> MOV_PROC
  FANART_MOV --> MOV_PROC
  TVDB & TMDB_TV & TUNARR --> TV_PROC
  FANART_TV --> TV_PROC
  MB_DB & MB_JSON & MUSICKIT & ITUNES & MB_REST --> MUS_PROC

  MOV_PROC & TV_PROC --> SUB_PROC
  OPENSUB & SUBDL --> SUB_PROC

  MOV_PROC --> NFO & ART
  TV_PROC  --> NFO & ART
  MUS_PROC --> NFO & ART
  SUB_PROC --> SUBS

  NFO & ART & SUBS --> PLEX[Plex Local Media Assets\nauto-refresh after run]
```

---

## Diagram 25 — Extended Script: First-Run Setup Dialog Flow

```mermaid
flowchart TD
  A([Script launched\nconfig missing or incomplete]) --> B[Check movies_library_roots]
  B --> C{Present?}
  C -- No --> D[Dialog: Do you have a Movies library?]
  D -- Yes --> E[macOS: Finder folder picker\nLinux/Win: terminal input]
  E --> F[Dialog: Add another Movies volume?]
  F -- Yes --> E
  F -- No --> G[Write movies_library_roots to config]
  D -- No --> G
  C -- Yes --> G
  G --> H[Same flow for TV library]
  H --> I[Same flow for Music library]
  I --> J[Check TMDB key]
  J --> K{Set and valid?}
  K -- No --> L[Dialog: Enter TMDB API key\nhttps://themoviedb.org/settings/api]
  L --> M[Validate: GET /configuration]
  M --> N{Valid?}
  N -- No --> O[Show error: invalid key\nRetry?]
  O -- Yes --> L
  O -- No --> P[Skip — movies unavailable this run]
  N -- Yes --> Q[Write tmdb.api_key to config]
  K -- Yes --> Q
  Q --> R[Same flow for TVDB key]
  R --> S[FanArt.tv key: optional\nShow Skip button]
  S --> T[OpenSubtitles key: optional\nShow Skip button]
  T --> U[Apple MusicKit: optional\nShow Skip button]
  U --> V[Dialog: Force full rescan?\nYes = --force / No = selective]
  V --> W[Dialog: Save all settings to config?]
  W -- Yes --> X[Write config file]
  W -- No --> X2[Use in-memory for this run only]
  X & X2 --> Y([Begin processing])
```

---

## Diagram 26 — API Key Validation + 15-Day Revalidation Flow

```mermaid
flowchart TD
  A([Script startup]) --> B[Load config]
  B --> C[Check key_validation_state.json\nin cache_dir]
  C --> D{Cache exists?}
  D -- No --> E[Run full validation\nall configured keys]
  D -- Yes --> F{Any key last_validated\n> 15 days ago?}
  F -- No --> G[All keys valid — skip validation\nProceed to processing]
  F -- Yes --> H[Re-validate expired keys only]
  E & H --> I[For each key to validate]
  I --> J{Service?}
  J -- TMDB --> K[GET /configuration → 200?]
  J -- TVDB --> L[POST /v4/login → token?]
  J -- FanArt.tv --> M[GET /movies/0 → 200?]
  J -- OpenSubtitles --> N[GET /infos/user → 200?]
  J -- Apple MusicKit --> O[Sign JWT + test API call]
  K & L & M & N & O --> P{Passed?}
  P -- Yes --> Q[Write last_validated = now\nto key_validation_state.json]
  Q --> R{More keys?}
  R -- Yes --> I
  R -- No --> G
  P -- No --> S{--no-prompts mode?}
  S -- No --> T[Blocking dialog:\nKey for SERVICE has expired\nPlease enter a new key]
  T --> U[User enters new key]
  U --> V[Validate new key]
  V --> W{Valid?}
  W -- Yes --> Q
  W -- No --> X[Show error: still invalid\nRetry or Skip?]
  X -- Retry --> U
  X -- Skip --> Y[Log warning: SERVICE disabled this run\nContinue without it]
  S -- Yes --> Y
  Y --> R
```

---

## Diagram 27 — Subtitle Download + Embedding Flow

```mermaid
flowchart TD
  A([Video file found]) --> B[Read IMDb ID\nfrom Movie.nfo or tvshow.nfo]
  B --> C{sidecar exists?\nstem.lang.srt}
  C -- Yes --> D{embed_in_file enabled?}
  D -- Yes --> E[ffprobe: check for\nexisting subtitle stream]
  E --> F{Embedded sub found\nin correct language?}
  F -- Yes --> G[⏭ Skip — already complete]
  F -- No --> H[Subtitle needed: embed only]
  D -- No --> G
  C -- No --> I[Subtitle needed: download + embed]
  H & I --> J[Try OpenSubtitles]
  J --> K[Search by IMDb ID\n+ language code]
  K --> L{Result found?}
  L -- Yes --> M[POST /download → SRT URL]
  M --> N[Download SRT bytes]
  L -- No --> O[Try Subdl fallback]
  O --> P[Search by IMDb ID]
  P --> Q{Result found?}
  Q -- No --> R[⚠ No subtitle found\nlog warning, continue]
  Q -- Yes --> S[Download ZIP\nextract first .srt]
  N & S --> T{sidecar mode enabled?}
  T -- Yes --> U[Write stem.lang.srt]
  T -- No --> V
  U --> V{embed_in_file enabled?}
  V -- No --> W([Done])
  V -- Yes --> X{Container is MP4/M4V?}
  X -- No --> Y[⚠ embed skipped\nnot MP4/M4V container\nsidecar only]
  X -- Yes --> Z{ffmpeg on PATH?}
  Z -- No --> Y
  Z -- Yes --> AA[ffmpeg: copy streams\n+ add mov_text subtitle track\ntagged with ISO 639-2 lang]
  AA --> BB[Write to temp.mp4]
  BB --> CC{temp size ≥ 95%\nof original?}
  CC -- No --> DD[❌ Sanity check failed\ndelete temp, keep original]
  CC -- Yes --> EE[Replace original\nwith temp.mp4]
  EE --> W
  G --> W
```

---

## Diagram 28 — Music Provider Selection Flow

```mermaid
flowchart TD
  A([Artist or Album lookup needed]) --> B{Local PostgreSQL DB\nconfigured and skip=false?}
  B -- Yes --> C[MusicBrainzLocalProvider\nsearch_artist / get_album]
  C --> D{Found?}
  D -- Yes --> E([Return result])
  D -- No --> F
  B -- No --> F{JSON dump dir\nconfigured?}
  F -- Yes --> G[MusicBrainzJsonProvider\nread MBID JSON files]
  G --> H{Found?}
  H -- Yes --> E
  H -- No --> I
  F -- No --> I{Apple MusicKit\nenabled=true?}
  I -- Yes --> J[Generate ES256 JWT\nfrom .p8 key file]
  J --> K[MusicKit API search\nartist or album]
  K --> L{Found?}
  L -- Yes --> E
  L -- No --> M
  I -- No --> M[iTunes Search API\nalways active · no auth]
  M --> N[GET itunes.apple.com/search\nmedia=music · entity=album]
  N --> O{Found?}
  O -- Yes --> P[Rewrite art URL to 3000x3000\nre.sub 100x100bb → 3000x3000bb]
  P --> E
  O -- No --> Q[MusicBrainz REST API\nrate-limited 1 req/sec]
  Q --> R{Found?}
  R -- Yes --> E
  R -- No --> S[⚠ Log warning\nno metadata for this item]
```

---

## Diagram 29 — iTunes Search API vs Apple MusicKit Decision

```mermaid
flowchart TD
  A([Music library configured]) --> B{apple_musickit.enabled\nin config?}
  B -- No --> C[iTunes Search API only\nfree · zero auth · always active]
  B -- Yes --> D{.p8 key file exists\nat private_key_path?}
  D -- No --> E[⚠ MusicKit enabled but key missing\nFallback to iTunes Search API]
  D -- Yes --> F{cryptography package\ninstalled?}
  F -- No --> G[⚠ pip3 install cryptography needed\nFallback to iTunes Search API]
  F -- Yes --> H[Generate ES256 JWT token\nvalid for 6 months]
  H --> I[MusicKit API active\n+ iTunes as fallback]

  C --> J[Album art: 3000×3000\nURL substitution trick]
  E --> J
  G --> J
  I --> K[Album art: native 3000×3000\nfrom Apple catalog masters]

  J --> L[artist.nfo · album.nfo · track.nfo\nBasic metadata\ntitle · year · genre · label]
  K --> M[artist.nfo · album.nfo · track.nfo\nRich metadata\n+ ISRC · composer · explicit flag]

  L & M --> N([appleid tag written\nto all music NFOs])
```

---

## Diagram 30 — Base Script vs Extended Script: Which to Use

```mermaid
flowchart TD
  A([Do you have a music library\nin Plex?]) --> B{Yes / No}
  B -- No --> C[Use plex_metadata_generator.py\nLighter · no music dependencies]
  B -- Yes --> D[Use plex_metadata_generator_extended.py\nFull music support]

  C --> E{Do you want\nsubtitles?}
  D --> E
  E -- Yes --> F[Enable subtitles block in config\nOpenSubtitles API key recommended]
  E -- No --> G[Leave subtitles.enabled: false]

  D --> H{Large music library\nand slow REST API?}
  H -- Yes --> I{Have PostgreSQL\ninstalled?}
  I -- Yes --> J[Download MusicBrainz\nPostgreSQL dump\n~30 GB · instant lookups]
  I -- No --> K[Download MusicBrainz\nJSON dump\n~80 GB · no DB needed]
  H -- No --> L[MusicBrainz REST API\nworks fine for small libraries]

  D --> M{Have Apple Developer\naccount 99/yr?}
  M -- Yes --> N[Configure Apple MusicKit\nfor richer metadata + ISRC]
  M -- No --> O[iTunes Search API is sufficient\nfree · 3000x3000 art · works now]
```

---

## Diagram 31 — Extended Script: Complete Run Sequence

```mermaid
sequenceDiagram
  participant CLI as CLI / Scheduler
  participant Script as Extended Script
  participant Dialog as Setup Dialogs
  participant Val as Key Validator
  participant Movie as Movie Processor
  participant TV as TV Processor
  participant Music as Music Processor
  participant Sub as Subtitle Downloader
  participant Plex as Plex API

  CLI->>Script: python3 plex_metadata_generator_extended.py --media-type all

  Script->>Dialog: Check config completeness
  Dialog-->>Script: Paths + keys confirmed (or dialogs shown)

  Script->>Val: Check key_validation_state.json
  Val-->>Script: All valid (or blocking dialog for expired key)

  Script->>Movie: process_movie_library(workers=N)
  loop Each movie folder (parallel if workers>1)
    Movie->>Movie: _needs_nfo() + _missing_art()
    alt Already complete
      Movie->>Movie: ⏭ Skip — zero API calls
    else NFO or art missing
      Movie->>Movie: TMDb search → get details
      Movie->>Movie: Write Movie.nfo
      Movie->>Movie: Download poster/backdrop (TMDB)
      Movie->>Movie: Download clearart/disc/logo (FanArt.tv)
    end
  end

  Script->>TV: process_tv_library(workers=N)
  loop Each show folder (parallel if workers>1)
    TV->>TV: Check tvshow.nfo + show art
    alt Already complete
      TV->>TV: ⏭ Skip show-level
    else Missing
      TV->>TV: TVDb search → get details
      TV->>TV: Write tvshow.nfo + download show art
    end
    loop Each episode
      TV->>TV: Check episode.nfo + thumb
      alt Already complete
        TV->>TV: ⏭ Skip episode
      else Missing
        TV->>TV: Write episode.nfo + download thumb
      end
    end
  end

  Script->>Music: process_music_library(workers=N)
  loop Each artist (parallel if workers>1)
    Music->>Music: Try MB_DB → JSON → MusicKit → iTunes → MB_REST
    Music->>Music: Write artist.nfo + artist.jpg
    loop Each album
      Music->>Music: Write album.nfo + cover.jpg
      loop Each track
        Music->>Music: Write track.nfo
      end
    end
  end

  Script->>Sub: SubtitleDownloader (if enabled)
  loop Each video file
    Sub->>Sub: Check sidecar + embedded sub
    alt Already complete
      Sub->>Sub: ⏭ Skip
    else Missing
      Sub->>Sub: OpenSubtitles search by IMDb ID
      Sub->>Sub: Download .srt → write sidecar
      Sub->>Sub: ffmpeg embed mov_text track
    end
  end

  Script->>Plex: refresh_library(movies_key)
  Script->>Plex: refresh_library(tv_key)
  Script->>Plex: refresh_library(music_key)
  Plex-->>Script: 200 OK
  Script->>CLI: ✓ Done (N processed · M skipped · K errors)
