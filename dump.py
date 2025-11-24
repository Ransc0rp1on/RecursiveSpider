import requests
import os
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import threading
from queue import Queue
import argparse
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RecursiveDirectoryDownloader:
    def __init__(self, base_url, output_dir="./downloaded_files", delay=1, max_threads=5, verify_ssl=False):
        self.base_url = base_url.rstrip('/')
        self.output_dir = output_dir
        self.delay = delay
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.downloaded_files = set()
        self.failed_downloads = set()
        self.scanned_dirs = set()
        self.file_queue = Queue()
        self.max_threads = max_threads
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

    def parse_directory_listing(self, html_content, base_url):
        """Parse directory listing and extract all files and directories"""
        soup = BeautifulSoup(html_content, 'html.parser')
        items = {'files': [], 'directories': []}
        
        # Look for all links in the directory listing
        for link in soup.find_all('a'):
            href = link.get('href', '').strip()
            
            # Skip parent directory and self references
            if href in ['', '../', './', '/'] or href.startswith('?') or 'Parent Directory' in link.text:
                continue
            
            full_url = urljoin(base_url + '/', href)
            
            # Determine if it's a directory or file
            if href.endswith('/'):
                items['directories'].append(full_url)
            else:
                items['files'].append(full_url)
        
        return items

    def get_directory_contents(self, url):
        """Get all files and directories from a directory listing"""
        try:
            print(f"Scanning directory: {url}")
            response = self.session.get(url, timeout=30, verify=self.verify_ssl)
            response.raise_for_status()
            
            return self.parse_directory_listing(response.text, url)
            
        except Exception as e:
            print(f"Error scanning {url}: {e}")
            return {'files': [], 'directories': []}

    def download_file(self, file_url, local_path):
        """Download individual file"""
        try:
            if file_url in self.downloaded_files:
                return True
                
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Skip if file already exists
            if os.path.exists(local_path):
                print(f"File already exists, skipping: {local_path}")
                self.downloaded_files.add(file_url)
                return True
            
            print(f"Downloading: {file_url}")
            response = self.session.get(file_url, stream=True, timeout=60, verify=self.verify_ssl)
            response.raise_for_status()
            
            # Check if it's actually a file and not a directory listing
            content_type = response.headers.get('content-type', '')
            if 'text/html' in content_type and 'Index of' in response.text:
                print(f"Skipping directory listing disguised as file: {file_url}")
                return False
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Verify the file was created and has content
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                self.downloaded_files.add(file_url)
                print(f"✓ Successfully downloaded: {os.path.basename(local_path)}")
                return True
            else:
                raise Exception("Downloaded file is empty or doesn't exist")
                
        except Exception as e:
            print(f"✗ Failed to download {file_url}: {e}")
            self.failed_downloads.add(file_url)
            # Remove partially downloaded file
            if os.path.exists(local_path):
                os.remove(local_path)
            return False

    def worker(self):
        """Worker thread for downloading files"""
        while True:
            item = self.file_queue.get()
            if item is None:
                break
                
            file_url, local_path = item
            self.download_file(file_url, local_path)
            time.sleep(self.delay)  # Rate limiting between downloads
            self.file_queue.task_done()

    def get_local_path(self, url):
        """Convert URL to local file path"""
        parsed_url = urlparse(url)
        path = parsed_url.path.lstrip('/')
        
        # Remove trailing slash for directories
        if path.endswith('/'):
            path = path[:-1]
            
        # Sanitize path
        path = path.replace('../', '').replace('./', '')
            
        return os.path.join(self.output_dir, path)

    def crawl_directory(self, url):
        """Recursively crawl a directory and all its subdirectories"""
        if url in self.scanned_dirs:
            return
            
        self.scanned_dirs.add(url)
        contents = self.get_directory_contents(url)
        
        # Process all files in current directory
        for file_url in contents['files']:
            local_path = self.get_local_path(file_url)
            self.file_queue.put((file_url, local_path))
        
        # Recursively process all subdirectories
        for dir_url in contents['directories']:
            print(f"Found subdirectory: {dir_url}")
            self.crawl_directory(dir_url)

    def start_download(self):
        """Start the recursive download process"""
        # Start worker threads
        threads = []
        for i in range(self.max_threads):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()
            threads.append(t)
        
        # Start crawling from base URL
        print("Starting recursive directory crawl...")
        self.crawl_directory(self.base_url)
        
        # Wait for all downloads to complete
        self.file_queue.join()
        
        # Stop worker threads
        for _ in range(self.max_threads):
            self.file_queue.put(None)
            
        for t in threads:
            t.join()

    def generate_report(self):
        """Generate download report"""
        report_path = os.path.join(self.output_dir, "download_report.txt")
        
        with open(report_path, 'w') as f:
            f.write("Recursive Download Report\n")
            f.write("=" * 60 + "\n")
            f.write(f"Base URL: {self.base_url}\n")
            f.write(f"Total directories scanned: {len(self.scanned_dirs)}\n")
            f.write(f"Total files downloaded: {len(self.downloaded_files)}\n")
            f.write(f"Total failed downloads: {len(self.failed_downloads)}\n")
            f.write(f"Output directory: {self.output_dir}\n")
            f.write(f"SSL Verification: {'Enabled' if self.verify_ssl else 'Disabled'}\n\n")
            
            f.write("Scanned directories:\n")
            for directory in sorted(self.scanned_dirs):
                f.write(f"  📁 {directory}\n")
                
            f.write("\nDownloaded files:\n")
            for file in sorted(self.downloaded_files):
                f.write(f"  ✓ {file}\n")
                
            if self.failed_downloads:
                f.write("\nFailed downloads:\n")
                for file in sorted(self.failed_downloads):
                    f.write(f"  ✗ {file}\n")
        
        print(f"\nReport generated: {report_path}")

def main():
    parser = argparse.ArgumentParser(description='Recursive directory downloader')
    parser.add_argument('url', help='Base URL to download from')
    parser.add_argument('-o', '--output', default='./downloaded_files', 
                       help='Output directory (default: ./downloaded_files)')
    parser.add_argument('-d', '--delay', type=float, default=1,
                       help='Delay between requests in seconds (default: 1)')
    parser.add_argument('-t', '--threads', type=int, default=3,
                       help='Maximum number of concurrent downloads (default: 3)')
    parser.add_argument('--verify-ssl', action='store_true',
                       help='Verify SSL certificates (disabled by default)')
    
    args = parser.parse_args()
    
    downloader = RecursiveDirectoryDownloader(
        base_url=args.url,
        output_dir=args.output,
        delay=args.delay,
        max_threads=args.threads,
        verify_ssl=args.verify_ssl
    )
    
    try:
        print(f"Starting recursive download from: {args.url}")
        print(f"Output directory: {args.output}")
        print(f"Delay between requests: {args.delay}s")
        print(f"Max concurrent downloads: {args.threads}")
        print(f"SSL Verification: {args.verify_ssl}")
        print("=" * 60)
        
        downloader.start_download()
        downloader.generate_report()
        
        print(f"\nDownload completed!")
        print(f"Directories scanned: {len(downloader.scanned_dirs)}")
        print(f"Successfully downloaded: {len(downloader.downloaded_files)} files")
        print(f"Failed downloads: {len(downloader.failed_downloads)} files")
        
    except KeyboardInterrupt:
        print("\nDownload interrupted by user")
        downloader.generate_report()
    except Exception as e:
        print(f"An error occurred: {e}")
        downloader.generate_report()

if __name__ == "__main__":
    main()
