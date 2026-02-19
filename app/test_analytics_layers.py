"""Test analytics layers in the price map dashboard."""

from playwright.sync_api import sync_playwright, Page
import time

def test_analytics_layers():
    """Test the analytics layers feature."""
    print("🚀 Starting browser test for analytics layers...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Monitor console for errors
        console_errors = []
        def handle_console(msg):
            if msg.type == "error":
                error_text = msg.text
                console_errors.append(error_text)
                print(f"❌ Console error: {error_text}")
        page.on("console", handle_console)
        
        # Monitor analytics requests
        analytics_requests = []
        def handle_response(response):
            if "analytics" in response.url:
                status = response.status
                analytics_requests.append((response.url, status))
                print(f"📡 Analytics request: {response.url} - Status: {status}")
        page.on("response", handle_response)
        
        try:
            # Navigate to map dashboard
            print("📍 Navigating to http://localhost:4321/dashboard/map/")
            page.goto("http://localhost:4321/dashboard/map/")
            
            # Wait for page to load completely
            print("⏳ Waiting for page load and React hydration...")
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(2)  # Extra time for React hydration
            
            # Take initial screenshot
            page.screenshot(path="test_screenshots/01_initial.png", full_page=True)
            print("📸 Screenshot saved: test_screenshots/01_initial.png")
            
            # Check for Analytics Layers text
            content = page.content()
            has_analytics_text = "Analytics Layers" in content
            print(f"🔍 'Analytics Layers' text present: {has_analytics_text}")
            
            # Look for category checkboxes
            checkboxes = page.locator('input[type="checkbox"]').all()
            print(f"📦 Total checkboxes found: {len(checkboxes)}")
            
            if len(checkboxes) > 0:
                # Get first few checkboxes with their labels
                for i, checkbox in enumerate(checkboxes[:5]):
                    try:
                        # Try to find associated label
                        parent = checkbox.evaluate_handle("el => el.parentElement")
                        if parent:
                            text = parent.evaluate("el => el.textContent")
                            print(f"   Checkbox {i+1}: {text[:50] if text else 'No text'}")
                    except:
                        pass
                
                # Click first analytics checkbox (after metric/period selectors)
                if len(checkboxes) > 5:
                    print(f"\n🖱️  Clicking analytics checkbox (index 5)...")
                    checkboxes[5].click()
                    time.sleep(2)
                    page.screenshot(path="test_screenshots/02_layer_toggled.png")
                    print("📸 Screenshot saved: test_screenshots/02_layer_toggled.png")
            
            # Check URL for layers parameter
            current_url = page.url
            has_layers_param = "layers=" in current_url
            print(f"\n🔗 Current URL: {current_url}")
            print(f"🔗 URL has 'layers=' parameter: {has_layers_param}")
            
            # Look for specific analytics categories
            categories = ["Spatial Analysis", "Feature Impact", "Predictive Analytics"]
            print(f"\n📊 Checking for category sections...")
            for category in categories:
                # Check for text or buttons
                try:
                    element = page.get_by_text(category).first
                    if element.count() > 0:
                        print(f"   ✅ {category}: Found")
                        # Try to click to expand
                        element.click()
                        time.sleep(1)
                    else:
                        print(f"   ❌ {category}: Not found")
                except:
                    print(f"   ⚠️  {category}: Error checking")
            
            # Take final screenshot after interactions
            page.screenshot(path="test_screenshots/03_final.png", full_page=True)
            print("\n📸 Screenshot saved: test_screenshots/03_final.png")
            
            # Print summary
            print("\n" + "="*60)
            print("TEST SUMMARY")
            print("="*60)
            print(f"✅ Page loaded successfully")
            print(f"📦 Checkboxes found: {len(checkboxes)}")
            print(f"📡 Analytics requests: {len(analytics_requests)}")
            print(f"❌ Console errors: {len(console_errors)}")
            print(f"🔗 URL state sync: {'✅' if has_layers_param else '❌'}")
            
            if analytics_requests:
                print("\n📡 Analytics endpoints called:")
                for url, status in analytics_requests:
                    print(f"   - {url} ({status})")
            
            if console_errors:
                print("\n❌ Console errors:")
                for error in console_errors[:5]:  # First 5 errors
                    print(f"   - {error}")
            
            print("="*60)
            
            print("\n⏳ Keeping browser open for 10 seconds for manual inspection...")
            time.sleep(10)
            
        finally:
            browser.close()
            print("✅ Test complete!")

if __name__ == "__main__":
    import os
    os.makedirs("test_screenshots", exist_ok=True)
    test_analytics_layers()
