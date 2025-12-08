from playwright.sync_api import sync_playwright

def verify_dashboard():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            print("Navigating to dashboard...")
            page.goto("http://localhost:3000/dashboard")

            print("Waiting for dashboard to load...")
            # Wait for some element that indicates dashboard is loaded, e.g., timing tower
            page.wait_for_timeout(5000) # Give it 5 seconds to sync data

            # Take screenshot of the whole page
            page.screenshot(path="verification/dashboard_replay.png")
            print("Screenshot saved to verification/dashboard_replay.png")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_dashboard()
