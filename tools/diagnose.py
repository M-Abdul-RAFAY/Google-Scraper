"""
Diagnostic script to check Chrome and WebDriver setup
"""

import sys
import os
import subprocess
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def check_chrome_installation():
    """Check if Chrome is installed and get version"""
    print("Checking Chrome installation...")
    
    # Common Chrome paths on Windows
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME'))
    ]
    
    chrome_found = False
    for path in chrome_paths:
        if os.path.exists(path):
            print(f"✓ Chrome found at: {path}")
            chrome_found = True
            
            # Try to get version
            try:
                result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print(f"✓ Chrome version: {result.stdout.strip()}")
                else:
                    print("⚠ Could not get Chrome version")
            except Exception as e:
                print(f"⚠ Error getting Chrome version: {e}")
            break
    
    if not chrome_found:
        print("✗ Chrome not found in common locations")
        print("Please install Google Chrome from: https://www.google.com/chrome/")
        return False
    
    return True

def test_webdriver_manager():
    """Test WebDriver Manager"""
    print("\nTesting WebDriver Manager...")
    
    try:
        print("Attempting to download/install ChromeDriver...")
        driver_path = ChromeDriverManager().install()
        print(f"✓ ChromeDriver installed at: {driver_path}")
        
        # Check if the file exists and is executable
        if os.path.exists(driver_path):
            file_size = os.path.getsize(driver_path)
            print(f"✓ ChromeDriver file size: {file_size} bytes")
            
            if file_size < 1000:  # Suspiciously small file
                print("⚠ ChromeDriver file seems too small, might be corrupted")
                return False
        else:
            print("✗ ChromeDriver file not found after installation")
            return False
            
        return True
        
    except Exception as e:
        print(f"✗ WebDriver Manager failed: {e}")
        return False

def test_basic_webdriver():
    """Test basic WebDriver functionality"""
    print("\nTesting basic WebDriver functionality...")
    
    try:
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        # Use a fresh ChromeDriver
        print("Creating WebDriver instance...")
        driver_path = ChromeDriverManager(cache_valid_range=1).install()
        service = Service(driver_path)
        
        driver = webdriver.Chrome(service=service, options=options)
        
        print("✓ WebDriver created successfully")
        
        # Test navigation
        print("Testing navigation to Google...")
        driver.get("https://www.google.com")
        
        title = driver.title
        print(f"✓ Page loaded successfully. Title: {title}")
        
        driver.quit()
        print("✓ WebDriver test completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ WebDriver test failed: {e}")
        try:
            driver.quit()
        except:
            pass
        return False

def clear_webdriver_cache():
    """Clear WebDriver Manager cache"""
    print("\nClearing WebDriver cache...")
    
    try:
        import shutil
        from webdriver_manager.core.utils import get_browser_version_from_os
        
        # Try to clear cache
        cache_dir = os.path.expanduser("~/.wdm")
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            print("✓ WebDriver cache cleared")
        else:
            print("• No cache directory found")
        
        return True
        
    except Exception as e:
        print(f"⚠ Could not clear cache: {e}")
        return False

def main():
    """Run all diagnostic checks"""
    print("Chrome and WebDriver Diagnostic Tool")
    print("=" * 50)
    
    checks_passed = 0
    total_checks = 3
    
    # Check Chrome installation
    if check_chrome_installation():
        checks_passed += 1
    
    # Clear cache first
    clear_webdriver_cache()
    
    # Test WebDriver Manager
    if test_webdriver_manager():
        checks_passed += 1
    
    # Test basic WebDriver
    if test_basic_webdriver():
        checks_passed += 1
    
    print("\n" + "=" * 50)
    print(f"DIAGNOSTIC SUMMARY: {checks_passed}/{total_checks} checks passed")
    
    if checks_passed == total_checks:
        print("✓ All checks passed! Your system should work with the scraper.")
        print("\nYou can now run:")
        print("  python demo.py")
        print("  python examples.py")
    else:
        print("✗ Some checks failed. Recommendations:")
        
        if checks_passed == 0:
            print("1. Install Google Chrome browser")
            print("2. Run this script as Administrator")
            print("3. Check your antivirus/firewall settings")
        elif checks_passed == 1:
            print("1. Try running as Administrator")
            print("2. Temporarily disable antivirus")
            print("3. Check internet connection")
        else:
            print("1. Try running the scraper anyway")
            print("2. Use headless=True mode")

if __name__ == "__main__":
    main()
