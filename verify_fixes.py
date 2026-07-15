#!/usr/bin/env python3
"""
Verify that all timeout-causing collectors have been disabled.
Run this BEFORE pushing to GitHub to confirm fixes are in place.

Usage:
    python verify_fixes.py
"""

import os
import sys

def check_file_content(filepath, should_contain, should_not_contain=None):
    """Check if a file contains/doesn't contain specific text."""
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check required content
    if should_contain:
        if should_contain in content:
            print(f"✅ {filepath}: Found '{should_contain[:50]}...'")
            found = True
        else:
            print(f"❌ {filepath}: Missing '{should_contain[:50]}...'")
            return False
    
    # Check for content that shouldn't be there
    if should_not_contain:
        if should_not_contain not in content:
            print(f"✅ {filepath}: Correctly removed '{should_not_contain[:50]}...'")
        else:
            print(f"❌ {filepath}: Still contains '{should_not_contain[:50]}...'")
            return False
    
    return True

def main():
    print("=" * 70)
    print("VERIFYING FIXES FOR RENDER TIMEOUT")
    print("=" * 70)
    print()
    
    all_good = True
    
    # Check 1: Academic sources disabled
    print("1. Checking academic_sources.py...")
    if not check_file_content(
        'collectors/academic_sources.py',
        should_contain='Academic sources collector: DISABLED',
        should_not_contain='scrape_researchgate(source'
    ):
        all_good = False
    print()
    
    # Check 2: International news disabled
    print("2. Checking international_news.py...")
    if not check_file_content(
        'collectors/international_news.py',
        should_contain='International sources collector: DISABLED',
        should_not_contain='for site in config.INTERNATIONAL_SOURCES'
    ):
        all_good = False
    print()
    
    # Check 3: Official sources disabled
    print("3. Checking official_sources.py...")
    if not check_file_content(
        'collectors/official_sources.py',
        should_contain='Official sources collector: DISABLED',
        should_not_contain='for site in config.OFFICIAL_SOURCES'
    ):
        all_good = False
    print()
    
    # Check 4: Tests are updated
    print("4. Checking tests...")
    if not check_file_content(
        'tests/test_pipeline.py',
        should_contain='for url, _ in found:',  # Should unpack 2-tuple, not 3
    ):
        all_good = False
    print()
    
    # Check 5: Documentation exists
    print("5. Checking documentation...")
    docs = ['PERFORMANCE_OPTIMIZATION.md', 'DEPLOYMENT_CHECKLIST.md']
    for doc in docs:
        if os.path.exists(doc):
            print(f"✅ {doc} exists")
        else:
            print(f"❌ {doc} missing")
            all_good = False
    print()
    
    # Final result
    print("=" * 70)
    if all_good:
        print("✅ ALL FIXES VERIFIED - READY TO DEPLOY!")
        print()
        print("Next steps:")
        print("  1. git add .")
        print("  2. git commit -m 'Fix: Disable blocking collectors to prevent timeout'")
        print("  3. git push origin main")
        print("  4. Wait for Render to redeploy (2-3 minutes)")
        print("  5. Check Render logs for 'DISABLED' messages")
        print()
        return 0
    else:
        print("❌ SOME FIXES ARE MISSING - DO NOT DEPLOY YET")
        print()
        print("Please run:")
        print("  python -m unittest discover tests -v")
        print("And verify all tests pass before deploying.")
        print()
        return 1

if __name__ == '__main__':
    sys.exit(main())
