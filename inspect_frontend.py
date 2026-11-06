"""Frontend route inspection via HTTP."""
import urllib.request
import urllib.error
import re

base = "http://localhost:3000"
routes = [
    "/",
    "/auth/login",
    "/auth/signup", 
    "/onboarding/start",
    "/onboarding/profile",
    "/onboarding/review",
    "/app/twin",
    "/app/careers",
    "/app/skills",
    "/app/roadmap",
    "/app/interview",
    "/app/trust",
]

print("=== Frontend Route Inspection (http://localhost:3000) ===")
for route in routes:
    try:
        url = base + route
        r = urllib.request.urlopen(url, timeout=8)
        content = r.read().decode('utf-8', errors='replace')[:500]
        status = r.status
        # Check for common issues
        has_404 = "<title>404</title>" in content.lower() or 'href="/404"' in content
        has_500 = "500" in content and "error" in content.lower()
        has_empty = "empty" in content.lower() and "state" in content.lower()
        has_meaningful = len(content) > 200 and "<title>" in content
        
        print(f"  {route}: {status}")
        if has_404: print(f"    -> 404 Not Found")
        if has_500: print(f"    -> 500 Error")  
        if has_empty: print(f"    -> Empty state")
        if has_meaningful and not has_404 and not has_500:
            print(f"    -> Renders with content ({len(content)} chars)")
            # Show first title tag
            m = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
            if m:
                print(f"      Title: {m.group(1)}")
    except urllib.error.HTTPError as e:
        content = e.read().decode('utf-8', errors='replace')[:300]
        print(f"  {route}: {e.code} - {content[:150]}")
    except Exception as e:
        print(f"  {route}: EXCEPTION - {e}")