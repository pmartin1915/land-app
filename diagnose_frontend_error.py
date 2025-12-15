"""
Alabama Auction Watcher - Frontend Error Diagnostic Script
Quick diagnostic tool for next AI instance to identify the localhost:5173 error

Run this first to get complete system status and error analysis.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
import socket

def check_port(host, port):
    """Check if a port is open"""
    try:
        socket.create_connection((host, port), timeout=1)
        return True
    except:
        return False

def run_command(command, timeout=5):
    """Run a command and return output"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as e:
        return "", str(e), 1

def main():
    print("=" * 60)
    print("ALABAMA AUCTION WATCHER - FRONTEND ERROR DIAGNOSTIC")
    print("=" * 60)
    print()

    # 1. Basic system info
    print("1. SYSTEM STATUS")
    print("-" * 20)
    print(f"Platform: {os.name}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Python version: {sys.version.split()[0]}")
    print()

    # 2. Check critical files
    print("2. CRITICAL FILES CHECK")
    print("-" * 25)
    critical_files = [
        "Alabama Auction Watcher.bat",
        "launchers/cross_platform/smart_launcher.py",
        "streamlit_app/app.py",
        "frontend/package.json",
        "frontend/vite.config.js",
        "alabama_auction_watcher.db"
    ]

    for file in critical_files:
        exists = "EXISTS" if os.path.exists(file) else "MISSING"
        if exists == "EXISTS":
            size = os.path.getsize(file)
            print(f"  {file}: {exists} ({size} bytes)")
        else:
            print(f"  {file}: {exists}")
    print()

    # 3. Port status check
    print("3. PORT STATUS CHECK")
    print("-" * 20)
    ports_to_check = [5173, 8000, 8501, 3000, 8080]
    for port in ports_to_check:
        status = "OPEN" if check_port("localhost", port) else "CLOSED"
        print(f"  localhost:{port}: {status}")
    print()

    # 4. Frontend analysis
    print("4. FRONTEND DIRECTORY ANALYSIS")
    print("-" * 32)
    frontend_dir = Path("frontend")
    if frontend_dir.exists():
        print(f"  Frontend directory: EXISTS")

        # Check package.json
        package_json = frontend_dir / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    pkg = json.load(f)
                print(f"  Package name: {pkg.get('name', 'Unknown')}")
                print(f"  Version: {pkg.get('version', 'Unknown')}")

                scripts = pkg.get('scripts', {})
                print("  Available scripts:")
                for script, command in scripts.items():
                    print(f"    {script}: {command}")

                deps = pkg.get('dependencies', {})
                dev_deps = pkg.get('devDependencies', {})
                print(f"  Dependencies: {len(deps)} runtime, {len(dev_deps)} dev")

                # Check for Vite specifically
                if 'vite' in dev_deps or 'vite' in deps:
                    print("  Framework: Vite detected")
                if 'react' in deps:
                    print("  Framework: React detected")

            except Exception as e:
                print(f"  Error reading package.json: {e}")
        else:
            print("  package.json: MISSING")

        # Check if node_modules exists
        node_modules = frontend_dir / "node_modules"
        print(f"  node_modules: {'EXISTS' if node_modules.exists() else 'MISSING'}")

        # List key files
        key_files = ['vite.config.js', 'index.html', 'src/main.jsx', 'src/main.tsx']
        print("  Key files:")
        for file in key_files:
            file_path = frontend_dir / file
            status = "EXISTS" if file_path.exists() else "MISSING"
            print(f"    {file}: {status}")
    else:
        print("  Frontend directory: MISSING")
    print()

    # 5. Check running processes
    print("5. RUNNING PROCESSES")
    print("-" * 20)
    stdout, stderr, code = run_command("tasklist /FI \"IMAGENAME eq node.exe\"")
    if "node.exe" in stdout:
        print("  Node.js processes found:")
        print(f"    {stdout}")
    else:
        print("  No Node.js processes running")

    stdout, stderr, code = run_command("tasklist /FI \"IMAGENAME eq python.exe\"")
    if "python.exe" in stdout:
        lines = stdout.split('\n')
        python_processes = [line for line in lines if 'python.exe' in line]
        print(f"  Python processes: {len(python_processes)} running")
    else:
        print("  No Python processes running")
    print()

    # 6. Database validation
    print("6. DATABASE STATUS")
    print("-" * 18)
    try:
        import sqlite3
        conn = sqlite3.connect('alabama_auction_watcher.db')
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM properties")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM properties WHERE total_description_score > 0")
        enhanced = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM properties WHERE rank IS NOT NULL")
        ranked = cursor.fetchone()[0]

        conn.close()

        print(f"  Total properties: {total}")
        print(f"  Enhanced scoring: {enhanced} ({enhanced/total*100:.1f}%)")
        print(f"  Investment rankings: {ranked} ({ranked/total*100:.1f}%)")

        if total == 1550 and enhanced == total and ranked == total:
            print("  Database status: PERFECT - Ready for production")
        else:
            print("  Database status: Issues detected")

    except Exception as e:
        print(f"  Database check failed: {e}")
    print()

    # 7. Smart launcher analysis
    print("7. SMART LAUNCHER ANALYSIS")
    print("-" * 28)
    smart_launcher = Path("launchers/cross_platform/smart_launcher.py")
    if smart_launcher.exists():
        try:
            with open(smart_launcher, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if "5173" in content:
                print("  Port 5173 referenced in smart_launcher.py")
                lines_with_5173 = [i+1 for i, line in enumerate(content.split('\n')) if '5173' in line]
                print(f"    Found on lines: {lines_with_5173}")
            else:
                print("  Port 5173 NOT found in smart_launcher.py")

            if "localhost" in content:
                print("  Localhost references found in smart_launcher.py")

            if "streamlit" in content.lower():
                print("  Streamlit integration detected")

        except Exception as e:
            print(f"  Error analyzing smart_launcher.py: {e}")
    else:
        print("  smart_launcher.py: MISSING")
    print()

    # 8. Recommendations
    print("8. IMMEDIATE NEXT STEPS")
    print("-" * 25)

    if not os.path.exists("frontend"):
        print("  1. Frontend directory missing - may be Streamlit-only system")
        print("  2. Check if launcher should use Streamlit instead")
    elif not os.path.exists("frontend/node_modules"):
        print("  1. Run: cd frontend && npm install")
        print("  2. Then: npm run dev")
    elif not check_port("localhost", 5173):
        print("  1. Frontend exists but server not running")
        print("  2. Run: cd frontend && npm run dev")
        print("  3. Or build static version: npm run build")
    else:
        print("  1. Port 5173 is open - check launcher configuration")
        print("  2. May be URL/routing issue in smart_launcher.py")

    if os.path.exists("streamlit_app/app.py"):
        print("  Alternative: Reconfigure launcher to use Streamlit (port 8501)")

    print()
    print("=" * 60)
    print("DIAGNOSTIC COMPLETE - Use findings to resolve frontend error")
    print("=" * 60)

if __name__ == "__main__":
    main()