# Plex Metadata System - Workflow & Signal Diagrams

## 1. System Architecture Overview

```mermaid
graph TB
    subgraph "Input Sources"
        A1["TMDB API"]
        A2["TVDB API"]
        A3["Spotify API"]
        A4["MusicBrainz API"]
        A5["Embedded Metadata<br/>in Video Files"]
    end
    
    subgraph "Processing Layer"
        B1["NFO Creator<br/>scraper.py"]
        B2["NFO Creator<br/>extract_artwork.py"]
        B3["Metadata Generator<br/>plex_metadata_generator"]
    end
    
    subgraph "Output Layer"
        C1["NFO Files<br/>tvshow.nfo<br/>movie.nfo<br/>season.nfo<br/>episode.nfo<br/>album.nfo<br/>track.nfo"]
        C2["Artwork Files<br/>poster.jpg<br/>folder.jpg<br/>banner.jpg"]
    end
    
    subgraph "Plex Library"
        D1["Plex Media Server"]
        D2["Local Media<br/>Agent"]
    end
    
    subgraph "Scheduling"
        E1["Systemd Timer"]
        E2["Cron"]
        E3["Docker"]
    end
    
    A1 --> B1
    A1 --> B3
    A2 --> B1
    A2 --> B3
    A3 --> B3
    A4 --> B3
    A5 --> B2
    
    B1 --> C1
    B2 --> C2
    B3 --> C1
    B3 --> C2
    
    C1 --> D2
    C2 --> D2
    D2 --> D1
    
    E1 --> B3
    E2 --> B3
    E3 --> B3
```

---

## 2. NFO Creator Workflow

```mermaid
flowchart LR
    A["📁 Raw Library<br/>Messy Names<br/>No Metadata"] 
    
    B["📝 rename_movies.py<br/>─────────────<br/>Cleans filenames<br/>Removes junk<br/>Standardizes format"]
    
    C["🔍 Manual Review<br/>─────────────<br/>Verify names<br/>Check results"]
    
    D["📥 scraper.py<br/>─────────────<br/>Queries TMDB/TVDB<br/>Generates NFO<br/>Downloads artwork"]
    
    E["🖼️ extract_artwork.py<br/>─────────────<br/>Extracts embedded<br/>artwork from video<br/>Saves as JPEG"]
    
    F["✅ Plex Library<br/>─────────────<br/>Metadata visible<br/>Artwork displayed<br/>Ready to use"]
    
    A --> B
    B --> C
    C -->|Approved| D
    C -->|Issues| B
    D --> E
    E --> F
```

---

## 3. Metadata Generator Workflow

```mermaid
flowchart LR
    A["🕐 Daily Schedule<br/>2 AM Trigger<br/>Via systemd/cron"]
    
    B["📚 Detect Library<br/>─────────────<br/>TV shows?<br/>Music?<br/>Both?"]
    
    C["🔎 Query Metadata<br/>─────────────<br/>API: TMDB<br/>API: TVDB<br/>API: Spotify<br/>API: MusicBrainz"]
    
    D["📄 Generate NFO<br/>─────────────<br/>Show/Album info<br/>Episode/Track info<br/>Download artwork<br/>Cache locally"]
    
    E["🌐 Plex Refresh<br/>─────────────<br/>HTTP API call<br/>Trigger scan<br/>Update UI"]
    
    F["✅ Library Updated<br/>─────────────<br/>New metadata<br/>Artwork displayed<br/>Metadata current"]
    
    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
```

---

## 4. Integrated Workflow (Both Systems)

```mermaid
flowchart TD
    A["🚀 New Library Setup"]
    
    B["Step 1: Use NFO Creator<br/>─────────────────────"]
    B1["rename_movies.py<br/>Clean filenames"]
    B2["scraper.py<br/>Generate metadata"]
    B3["extract_artwork.py<br/>Extract artwork"]
    
    C["Step 2: Verify in Plex<br/>─────────────────────"]
    C1["Set Local Media<br/>Agent to #1"]
    C2["Manual library refresh<br/>Check coverage"]
    
    D["Step 3: Setup Generator<br/>─────────────────────"]
    D1["Install files<br/>Configure API keys<br/>Set library paths"]
    D2["Enable scheduling<br/>Systemd/Cron/Docker"]
    
    E["🎯 Ongoing Operation<br/>─────────────────────"]
    E1["Daily automatic<br/>metadata updates"]
    E2["New content<br/>discovered"]
    E3["Metadata refreshed<br/>+ artwork"]
    
    A --> B
    B --> B1
    B1 --> B2
    B2 --> B3
    B3 --> C
    C --> C1
    C1 --> C2
    C2 --> D
    D --> D1
    D1 --> D2
    D2 --> E
    E --> E1
    E1 --> E2
    E2 --> E3
    E3 -.->|Loop| E1
```

---

## 5. Signal Flow: Metadata Generator

```mermaid
sequenceDiagram
    actor Timer as Systemd<br/>Timer
    participant Gen as Metadata<br/>Generator
    participant API as TMDB/TVDB/<br/>Spotify API
    participant Cache as Local<br/>Cache
    participant FS as Filesystem<br/>NFO/JPEG
    participant Plex as Plex<br/>Server
    
    Timer ->> Gen: 2 AM Trigger
    
    Gen ->> Gen: Detect libraries<br/>(TV, Music, Both)
    
    loop For Each Show/Album
        Gen ->> API: Query metadata
        API -->> Gen: Return data
        
        alt Data found
            Gen ->> Cache: Check cache
            alt Cache miss
                Gen ->> API: Download artwork
                API -->> Gen: Image bytes
                Gen ->> Cache: Store image
            else Cache hit
                Cache -->> Gen: Return cached image
            end
        else Data not found
            Gen ->> API: Try fallback source
        end
        
        Gen ->> FS: Write NFO file
        Gen ->> FS: Write artwork JPEG
    end
    
    Gen ->> Plex: HTTP POST<br/>/library/refresh
    Plex ->> Plex: Scan library
    Plex ->> FS: Read NFO files
    Plex ->> Plex: Update database
    Plex -->> Gen: 200 OK
    
    Gen ->> Gen: Log completion
```

---

## 6. Signal Flow: NFO Creator

```mermaid
sequenceDiagram
    actor User as User
    participant Rename as rename_<br/>movies.py
    participant Scraper as scraper.py
    participant Extract as extract_<br/>artwork.py
    participant API as TMDB/TVDB<br/>API
    participant FS as Filesystem
    participant Log as Progress<br/>Log
    
    User ->> Rename: Run with folder path
    Rename ->> FS: Scan directory
    Rename ->> Log: Track changes
    Rename ->> Rename: Apply rules<br/>(dry run)
    Rename -->> User: Show preview
    
    User ->> Rename: Run with --rename flag
    loop For Each File
        Rename ->> FS: Move/rename file
        Rename ->> Log: Log each rename
    end
    Rename -->> User: Complete
    
    User ->> Scraper: Run scraper.py
    loop For Each Show/Movie
        Scraper ->> API: Query TMDB/TVDB
        API -->> Scraper: Metadata
        Scraper ->> FS: Write NFO file
        Scraper ->> Log: Log progress
    end
    Scraper -->> User: Complete
    
    User ->> Extract: Run extract_artwork.py
    loop For Each Video File
        Extract ->> FS: Read MP4/M4V
        Extract ->> Extract: Extract artwork
        Extract ->> FS: Save poster.jpg
        Extract ->> Log: Log extraction
    end
    Extract -->> User: Complete
```

---

## 7. Data Flow: TV Show Processing

```mermaid
graph TD
    A["🎬 TV Show Folder<br/>Show Name (Year)<br/>Season 1/"] --> B["📊 Library Scanner<br/>─────────────<br/>Detect show<br/>Find episodes<br/>Check for NFO"]
    
    B --> C{NFO<br/>Exists?}
    
    C -->|Yes| D["✅ Use Existing<br/>─────────────<br/>Parse NFO<br/>Extract metadata<br/>Display in Plex"]
    
    C -->|No| E["🔍 Query APIs<br/>─────────────<br/>TMDB search<br/>TVDB search<br/>Fallback: Tunarr"]
    
    E --> F["📥 Fetch Metadata<br/>─────────────<br/>Title<br/>Year<br/>Plot<br/>Rating<br/>Runtime"]
    
    F --> G["🖼️ Download Artwork<br/>─────────────<br/>Poster URL<br/>Download image<br/>Cache locally"]
    
    G --> H["📝 Generate NFO<br/>─────────────<br/>tvshow.nfo<br/>season.nfo<br/>episode.nfo"]
    
    H --> I["💾 Write Files<br/>─────────────<br/>Save to disk<br/>Set permissions<br/>Verify write"]
    
    I --> D
    
    D --> J["🌐 Plex Refresh<br/>─────────────<br/>Scan folder<br/>Read NFO<br/>Parse metadata"]
    
    J --> K["✨ Plex UI<br/>─────────────<br/>Display title<br/>Show cover art<br/>List episodes"]
```

---

## 8. Data Flow: Music Album Processing

```mermaid
graph TD
    A["🎵 Artist/Album Folder<br/>Artist Name/<br/>Album Name/"] --> B["📊 Library Scanner<br/>─────────────<br/>Detect artist<br/>Find albums<br/>Scan tracks"]
    
    B --> C{NFO<br/>Exists?}
    
    C -->|Yes| D["✅ Use Existing<br/>─────────────<br/>Parse NFO<br/>Extract data"]
    
    C -->|No| E["🔍 Query APIs<br/>─────────────<br/>Spotify search<br/>MusicBrainz fallback"]
    
    E --> F["📥 Fetch Metadata<br/>─────────────<br/>Album title<br/>Artist name<br/>Release year<br/>Track count"]
    
    F --> G["🖼️ Download Cover<br/>─────────────<br/>Spotify API<br/>High-res image<br/>Cache locally"]
    
    G --> H["📝 Generate NFO<br/>─────────────<br/>artist.nfo<br/>album.nfo<br/>track.nfo"]
    
    H --> I["💾 Write Files<br/>─────────────<br/>Save to disk<br/>Set permissions<br/>Verify write"]
    
    I --> D
    
    D --> J["🌐 Plex Refresh<br/>─────────────<br/>Scan folder<br/>Read NFO<br/>Parse metadata"]
    
    J --> K["✨ Plex UI<br/>─────────────<br/>Display album<br/>Show cover art<br/>List tracks"]
```

---

## 9. Scheduling Architecture

```mermaid
graph TD
    subgraph "Option 1: Systemd (Recommended)"
        A1["plex-metadata-<br/>generator.timer"] -->|At 2:00 AM| A2["plex-metadata-<br/>generator.service"]
        A2 --> A3["Run script"]
    end
    
    subgraph "Option 2: Cron"
        B1["crontab Entry<br/>0 2 * * *"] -->|Daily 2 AM| B2["plex-metadata-<br/>generator-cron"]
        B2 --> B3["Run script"]
    end
    
    subgraph "Option 3: Docker"
        C1["Docker Container<br/>docker-compose up"] -->|Continuous| C2["Script runs<br/>on schedule"]
    end
    
    A3 --> D["📊 Metadata Generation<br/>─────────────<br/>Process TV<br/>Process Music<br/>Download artwork"]
    B3 --> D
    C2 --> D
    
    D --> E["💾 Write NFO/JPEG<br/>to filesystem"]
    E --> F["🌐 Plex Library<br/>Refresh API Call"]
    F --> G["✅ Updated Library<br/>Metadata current"]
```

---

## 10. Error Handling & Fallback Chain

```mermaid
graph TD
    A["Query for<br/>Show/Album"] --> B["Try Primary<br/>Source"]
    
    B --> C{Match<br/>Found?}
    
    C -->|Yes| D["✅ Get Metadata<br/>Primary source"]
    
    C -->|No| E["Try Fallback 1<br/>Source"]
    
    E --> F{Match<br/>Found?}
    
    F -->|Yes| G["✅ Get Metadata<br/>Fallback 1"]
    
    F -->|No| H["Try Fallback 2<br/>Source"]
    
    H --> I{Match<br/>Found?}
    
    I -->|Yes| J["✅ Get Metadata<br/>Fallback 2"]
    
    I -->|No| K["⚠️ No Match<br/>Create Basic NFO<br/>Title only<br/>No artwork"]
    
    D --> L["📝 Generate NFO<br/>Download Artwork"]
    G --> L
    J --> L
    K --> L
    
    L --> M["💾 Write to<br/>Filesystem"]
```

---

## 11. Library Structure Hierarchy

```mermaid
graph TD
    A["Media Root<br/>/mnt/media"]
    
    A -->|TV| B["TV Shows<br/>/mnt/media/TV"]
    A -->|Music| C["Music<br/>/mnt/media/Music"]
    A -->|Movies| D["Movies<br/>/mnt/media/Movies"]
    
    B --> B1["Show Name/"]
    B1 --> B2["tvshow.nfo<br/>poster.jpg"]
    B1 --> B3["Season 1/"]
    B3 --> B4["season.nfo<br/>episode.nfo"]
    B3 --> B5["episode.mkv"]
    
    C --> C1["Artist Name/"]
    C1 --> C2["artist.nfo<br/>artist.jpg"]
    C1 --> C3["Album Name/"]
    C3 --> C4["album.nfo<br/>folder.jpg<br/>track.nfo"]
    C3 --> C5["track.mp3"]
    
    D --> D1["Movie Name (Year)/"]
    D1 --> D2["movie.nfo<br/>poster.jpg"]
    D1 --> D3["movie.mkv"]
```

---

## 12. API Priority Chain: Metadata Generator

```mermaid
graph LR
    subgraph "TV Shows"
        T1["TVDb<br/>Primary"]
        T2["TMDb<br/>Fallback 1"]
        T3["Tunarr<br/>Fallback 2"]
    end
    
    subgraph "Music"
        M1["Spotify<br/>Primary"]
        M2["MusicBrainz<br/>Fallback"]
    end
    
    subgraph "Combined"
        C1["Try Primary"]
        C2["If no match:<br/>Try Fallback 1"]
        C3["If no match:<br/>Try Fallback 2"]
        C4["If no match:<br/>Create basic NFO"]
    end
    
    T1 --> C1
    T2 --> C2
    T3 --> C3
    M1 --> C1
    M2 --> C2
    
    C1 -->|Success| D["Generate<br/>Full Metadata"]
    C2 -->|Success| D
    C3 -->|Success| D
    C4 -->|No match| E["Generate<br/>Basic Metadata<br/>Title only"]
```

---

## 13. Comparison Matrix

```mermaid
graph TB
    subgraph "Feature Comparison"
        A["NFO Creator<br/>─────────────<br/>✅ Batch rename<br/>✅ Extract artwork<br/>✅ Direct API scrape<br/>❌ No scheduling<br/>❌ No music support<br/>❌ Manual operation"]
        
        B["Metadata Generator<br/>─────────────<br/>✅ Automatic scheduling<br/>✅ Music support<br/>✅ API fallback chain<br/>✅ Plex integration<br/>✅ Caching<br/>❌ No extraction<br/>❌ No rename"]
        
        C["Both Together<br/>─────────────<br/>✅ Initial batch setup<br/>✅ Ongoing automation<br/>✅ Complete coverage<br/>✅ Artwork extraction<br/>✅ Filename cleanup<br/>✅ All media types"]
    end
    
    A -.-> C
    B -.-> C
```

---

**These diagrams provide complete visibility into:**
- System architecture and data flow
- Workflow sequences for both systems
- Signal flows between components
- Scheduling mechanisms
- Error handling and fallback chains
- Library organization
- Integration scenarios
