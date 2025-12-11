import os
import time
import requests
import base64
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin, urlparse
import traceback

print("Starting Final Scraper Script...")

def clean_filename(url):
    """Generates a safe filename from the URL."""
    path = urlparse(url).path
    name = os.path.basename(path)
    if not name:
        name = "index.jpg" 
    name = name.split('?')[0] # Remove query params
    return name

def clean_text(text):
    """Cleans text to be safe for folder names."""
    return "".join([c for c in text if c.isalpha() or c.isdigit() or c==' ' or c=='-']).strip()

def download_image(driver, img_url, folder_path):
    """
    Downloads image using Selenium to bypass anti-bot checks.
    Uses robust JS fetch + base64 conversion.
    """
    try:
        filename = clean_filename(img_url)
        filepath = os.path.join(folder_path, filename)
        
        # Check if already exists
        if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
            print(f"  [Skip] {filename}, already exists.")
            return

        # Ensure directory exists (redundant safety)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # JS to fetch image as blob -> base64
        js_script = """
            var uri = arguments[0];
            var callback = arguments[1];
            fetch(uri)
                .then(response => {
                    if (!response.ok) throw new Error('Network response was not ok');
                    return response.blob();
                })
                .then(blob => {
                    var reader = new FileReader();
                    reader.onload = function() {
                        callback(reader.result);
                    };
                    reader.readAsDataURL(blob);
                })
                .catch(error => {
                    callback('ERROR: ' + error.message);
                });
        """
        
        # Execute async script
        result = driver.execute_async_script(js_script, img_url)
        
        if result and str(result).startswith('data:image'):
            # Parse base64
            header, encoded = result.split(",", 1)
            data = base64.b64decode(encoded)
            
            if len(data) < 1000:
                print(f"   [Skip-Small] {filename} is too small ({len(data)} bytes).")
            else:
                with open(filepath, 'wb') as f:
                    f.write(data)
                print(f"  [Downloaded] {filename} ({len(data)} bytes)")
                
        elif result and str(result).startswith('ERROR'):
            print(f"  [JS Error] {img_url}: {result}")
        else:
             print(f"  [Fail] Could not retrieve content for {img_url}")

    except Exception as e:
        print(f"  [Exception] Error accessing {img_url}: {e}")

def scrape_leaf_page(driver, url, output_folder):
    """Scrapes images from a specific leaf page (subsection)."""
    print(f"  > Scraping leaf page: {url}")
    try:
        driver.get(url)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3) 
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        media_items = set()
        
        # 1. Look for High-Res links (anchors linking to images)
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Check for image extensions
            if any(href.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                # Exclude thumbnails unless they are the only option (heuristic)
                if "150x150" not in href:
                    full_url = urljoin(url, href)
                    media_items.add(full_url)

        # 2. Look for images directly (img tags)
        for img in soup.find_all('img', src=True):
            src = img['src']
            # Heuristic: If it's a thumbnail, try to strip suffixes to find the original
            if "150x150" in src:
               clean_src = src.replace("-150x150", "").replace("-300x300", "") 
               media_items.add(urljoin(url, clean_src))
            else:
               media_items.add(urljoin(url, src))
                 
        # Filter unwanted icons/logos
        final_targets = []
        for item in media_items:
            lower_item = item.lower()
            if 'icon' in lower_item or 'logo' in lower_item or 'gravatar' in lower_item:
                continue
            final_targets.append(item)
            
        print(f"    Found {len(final_targets)} potential image targets.")
        
        for img_url in final_targets:
            download_image(driver, img_url, output_folder)
            
    except Exception as e:
        print(f"    Error scraping leaf page {url}: {e}")

def main():
    # Setup Driver
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
    options.add_argument("--start-maximized")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    
    print("Initializing Chrome Driver...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    base_url = "https://medicine.nus.edu.sg/pathweb/normal-histology/"
    base_output_dir = "images_scraped"
    
    try:
        print(f"Navigating to {base_url}")
        driver.get(base_url)
        
        print("\n" + "="*50)
        print("ACTION REQUIRED: Please solve any Captchas/Incapsula challenges in the browser.")
        print("Ensure the 'Normal Histology' page is fully visible.")
        print("="*50 + "\n")
        
        input("Press Enter here once the page is fully loaded and visible...")
        
        # --- PHASE 1: Dynamic Discovery ---
        print("Analyzing Main Page Structure...")
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        structure = {} # { "Section Name": [ {"name": "Subsection Name", "url": "..."} ] }
        current_section = "Uncategorized"
        
        # Locate main content area to avoid sidebar/footer noise
        content_area = soup.find('main') or soup.find('article') or soup.find('body')
        
        # Linear scan for headers and links
        # Heuristic: H tags (1-5) start new sections, Links belong to current section
        for element in content_area.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'a']):
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5']:
                header_text = clean_text(element.get_text())
                if len(header_text) > 2 and "Histology" not in header_text: 
                    current_section = header_text
                    if current_section not in structure:
                        structure[current_section] = []
                        
            elif element.name == 'a' and element.get('href'):
                href = element.get('href')
                link_text = clean_text(element.get_text())
                full_url = urljoin(base_url, href)
                
                # Check for validity: must be a subpage of/related to base_url
                if base_url in full_url and full_url != base_url and len(link_text) > 2:
                    if current_section not in structure:
                        structure[current_section] = []
                    
                    # Avoid duplicates
                    if not any(item['url'] == full_url for item in structure[current_section]):
                         structure[current_section].append({'name': link_text, 'url': full_url})

        # Remove empty sections
        structure = {k: v for k, v in structure.items() if v}
        print(f"Identified {len(structure)} dynamically discovered sections.")
        
        # --- PHASE 2: Manual Supplements (The "Fix") ---
        # Add known missing items that dynamic scraping often misses due to flat text links or formatting
        print("Checking for missing known sections (Manual Overrides)...")
        
        # Define known missing structure
        # Add to "Gastrointestinal Tract" if it exists, else create it
        target_section = "Gastrointestinal Tract"
        manual_links = {
            "Appendix": "https://medicine.nus.edu.sg/pathweb/normal-histology/appendix/",
            "Tongue": "https://medicine.nus.edu.sg/pathweb/normal-histology/tongue/",
            "Tonsil": "https://medicine.nus.edu.sg/pathweb/normal-histology/tonsil/"
        }
        
        if target_section not in structure:
            structure[target_section] = []
            
        existing_urls = [item['url'] for item in structure[target_section]]
        
        for name, url in manual_links.items():
            if url not in existing_urls:
                print(f"  + Adding manual target: {target_section} -> {name}")
                structure[target_section].append({'name': name, 'url': url})

        # --- PHASE 3: Execution ---
        for section, subsections in structure.items():
            print(f"\nProcessing Section: {section}")
            section_path = os.path.join(base_output_dir, section)
            
            for item in subsections:
                sub_name = item['name']
                sub_url = item['url']
                
                # Folder: images_scraped / Section / Subsection
                target_folder = os.path.join(section_path, sub_name)
                
                print(f"  Subsection: {sub_name}")
                
                # Simple Resume Logic: If folder has > 2 images, assume done.
                if os.path.exists(target_folder):
                    existing_files = [f for f in os.listdir(target_folder) if f.lower().endswith(('.jpg', '.png'))]
                    if len(existing_files) > 0:
                        print(f"    [Resume] Skipping {sub_name}, already has {len(existing_files)} files.")
                        continue
                
                scrape_leaf_page(driver, sub_url, target_folder)
                time.sleep(1) # Be nice to server

    except Exception as e:
        print(f"Critical Error: {e}")
        traceback.print_exc()
    finally:
        print("Script finished.")

if __name__ == "__main__":
    main()
