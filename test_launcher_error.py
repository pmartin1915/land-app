"""
Test script to reproduce the exact launcher error
This will help the next AI instance see the problem clearly.
"""

import subprocess
import sys
import os
from pathlib import Path

def test_launcher_error():
    print("=" * 50)
    print("REPRODUCING DESKTOP LAUNCHER ERROR")
    print("=" * 50)
    print()

    # Test the main launcher
    bat_file = Path("Alabama Auction Watcher.bat")

    if bat_file.exists():
        print(f"Testing launcher: {bat_file}")
        print("This should reproduce the error:")
        print("'Development server not available and built version not found.'")
        print("'Server URL attempted: http://localhost:5173'")
        print()
        print("Launching in 3 seconds...")
        print("(Press Ctrl+C to cancel)")
        print()

        try:
            import time
            time.sleep(3)

            # Run the bat file and capture output
            result = subprocess.run([str(bat_file)],
                                  capture_output=True,
                                  text=True,
                                  timeout=10)

            print("LAUNCHER OUTPUT:")
            print("-" * 20)
            if result.stdout:
                print("STDOUT:")
                print(result.stdout)
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
            print(f"Return code: {result.returncode}")

        except subprocess.TimeoutExpired:
            print("Launcher timed out after 10 seconds")
        except KeyboardInterrupt:
            print("Test cancelled by user")
        except Exception as e:
            print(f"Error running launcher: {e}")

    else:
        print(f"ERROR: {bat_file} not found!")
        print("Cannot reproduce the launcher error")

    print()
    print("=" * 50)
    print("To fix this error, the next AI should:")
    print("1. Run: python diagnose_frontend_error.py")
    print("2. Follow the diagnostic recommendations")
    print("3. Ensure frontend server starts properly")
    print("4. Test desktop icon launches successfully")
    print("=" * 50)

if __name__ == "__main__":
    test_launcher_error()