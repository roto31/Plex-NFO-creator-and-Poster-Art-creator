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
