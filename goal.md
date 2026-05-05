# Goal

## Project
calibre-web-automated-book-downloader — a python project.

## Description
Shelfmark is a self-hosted web interface for searching and requesting books and audiobooks across multiple sources. It provides a Flask-based web application with:

- **Configuration System**: Dynamic settings with priority resolution (ENV > database > defaults)
- **Metadata Providers**: Plugin system for book metadata (Google Books, Hardcover, Open Library)
- **Release Sources**: Plugin system for downloadable releases (Prowlarr/torrent indexers, Newznab/usenet, IRC, direct download)
- **Download Clients**: Integration with torrent/usenet clients (qBittorrent, Transmission, SABnzbd, etc.)
- **Download Queue**: Thread-safe priority queue with cancellation support
- **Template-based Naming**: Configurable file naming with variable substitution
- **Caching**: Thread-safe in-memory cache with TTL for metadata and releases
- **Web API**: Flask REST API with SocketIO for real-time updates

## Scope
- ~30-40 production source files to implement (core modules)
- ~15-20 test files to write
- Focus on core functionality: config, models, cache, naming, queue, metadata providers, release sources, download clients, and basic web API
