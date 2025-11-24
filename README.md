# 🕷️ RecursiveSpider
A fast, multi-threaded **recursive directory downloader** that automatically crawls open web directory listings (Apache/Nginx/Lighttpd) and downloads all files while preserving the original folder structure.

RecursiveSpider is ideal for:
- Web security assessments  
- OSINT data extraction  
- Backups of publicly accessible directory listings  
- Automating large file collection tasks  

---

## ✨ Features

- 🔍 **Recursive crawling** of directory listings  
- 🔄 **Preserves directory structure** exactly as on the server  
- ⚡ **Multi-threaded downloads** (configurable)  
- 🧭 **Automatic detection of subdirectories & files**  
- 🛡️ **Graceful handling of SSL errors**, 404s, and HTML disguised as files  
- 📁 **Generates a detailed download report**  
- ⏱️ Configurable **delay between requests**  
- 🧼 Cleans and sanitizes file paths for safe storage  
- 📦 Works on Windows, Linux, and macOS  

---
Usage:

Basic usage:

```python download_script.py http://example.com/files```

With custom output directory:

```python download_script.py http://example.com/files -o ./my_downloads```

With slower requests (to avoid detection):

```python download_script.py http://example.com/files -d 2```

With single-threaded download:

```python download_script.py http://example.com/files -t 1```
