🕵️ OSINT Username Checker

A high-performance, asynchronous CLI tool designed for rapid username enumeration across 100+ platforms. Engineered for speed and precision using Python’s httpx and asyncio libraries.
🚀 Key Features

  Asynchronous Architecture: Scan 100+ sources in under 60 seconds.

  Intelligent Detection: Handles both HTTP status codes and "soft 404" response patterns.

  Stealth-Ready: Configurable rate limiting and User-Agent rotation to bypass basic anti-bot filters.

  Professional Output: Clean, color-coded CLI tables with export support for JSON and TXT.

  Extensible: Simple sites.json structure for adding custom platforms.

🛠️ Installation
Bash

# Clone the repository
git clone https://github.com/yourusername/osint-username-checker
cd osint-username-checker

# Set up environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

📖 Usage Guide
Basic Scan
Bash

python username_checker.py <username>

Advanced Recon (Stealth & Export)
Bash

# Slower rate limit for stealth, exporting to JSON
python username_checker.py <username> --rate-limit 1.5 --export json

⚙️ Configuration

Easily add new platforms by updating the sites.json file:
JSON

{
  "name": "NewPlatform",
  "url_template": "https://example.com/user/{username}",
  "detection_type": "status_code"
}

⚖️ Legal Disclaimer

This tool is for educational and authorized security testing only. The developer assumes no liability for misuse. Users must comply with local laws and platform Terms of Service.
👤 Developer & Credits

Developed by Anmoldeep Singh Khaira – Cybersecurity enthusiast and software developer.

LinkedIn: www.linkedin.com/in/anmoldeep-singh-khaira-249921280

Instagram: https://www.instagram.com/khaira_saab_001/


