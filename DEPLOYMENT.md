# Alabama Auction Watcher - Deployment Guide

Complete step-by-step deployment guide for production use of the Alabama Auction Watcher system.

## 📋 Prerequisites

### System Requirements
- **Python**: 3.10 or higher (tested with 3.13)
- **Operating System**: Windows, macOS, or Linux
- **Memory**: Minimum 2GB RAM (4GB+ recommended for large datasets)
- **Storage**: 1GB free space for data and logs
- **Internet**: Stable connection for web scraping

### Network Requirements
- **Outbound HTTPS**: Access to `www.revenue.alabama.gov` (port 443)
- **Local Ports**: 8501 (Streamlit dashboard) - configurable

## 🚀 Installation Steps

### 1. Clone Repository
```bash
git clone <your-repository-url>
cd auction-watcher
```

### 2. Python Environment Setup
```bash
# Create virtual environment (recommended)
python -m venv auction-env

# Activate environment
# Windows:
auction-env\Scripts\activate
# macOS/Linux:
source auction-env/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Verify Installation
```bash
# Test basic functionality
python scripts/parser.py --list-counties

# Test web scraping
python scripts/parser.py --scrape-county Baldwin --max-pages 1
```

## ⚙️ Configuration

### Environment Variables
Create a `.env` file in the project root:

```bash
# Logging configuration
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE=logs/auction_watcher.log # Optional log file path
LOG_DETAILED=false                # Detailed logging with function names

# Performance tuning
SCRAPING_DELAY=2.0               # Seconds between requests (respect ADOR)
MAX_CONCURRENT_REQUESTS=1        # Keep at 1 to be respectful
REQUEST_TIMEOUT=30               # HTTP request timeout in seconds

# Data storage
DATA_RETENTION_DAYS=30           # Days to keep raw scraped data
```

### Custom Configuration
Edit `config/settings.py` to customize:

```python
# Property filtering criteria
MIN_ACRES = 1.0                  # Minimum acreage
MAX_ACRES = 5.0                  # Maximum acreage
MAX_PRICE = 20000.0              # Maximum price

# Investment analysis weights
INVESTMENT_SCORE_WEIGHTS = {
    'price_per_acre': 0.4,       # Price competitiveness
    'acreage_preference': 0.3,   # Size preference
    'water_features': 0.2,       # Water feature bonus
    'assessed_value_ratio': 0.1  # Value ratio
}
```

## 🖥️ Production Deployment

### Option 1: Local Production Server

#### 1. Create Production Directory
```bash
mkdir -p /opt/auction-watcher
cp -r . /opt/auction-watcher/
cd /opt/auction-watcher
```

#### 2. Set Up Service User
```bash
# Create dedicated user (Linux/macOS)
sudo useradd -r -s /bin/false auction-watcher
sudo chown -R auction-watcher:auction-watcher /opt/auction-watcher
```

#### 3. Configure Systemd Service (Linux)
Create `/etc/systemd/system/auction-watcher.service`:

```ini
[Unit]
Description=Alabama Auction Watcher Dashboard
After=network.target

[Service]
Type=exec
User=auction-watcher
Group=auction-watcher
WorkingDirectory=/opt/auction-watcher
Environment=PATH=/opt/auction-watcher/auction-env/bin
ExecStart=/opt/auction-watcher/auction-env/bin/python -m streamlit run streamlit_app/app.py --server.port=8501 --server.address=0.0.0.0
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable auction-watcher
sudo systemctl start auction-watcher
```

### Option 2: Docker Deployment

#### 1. Create Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 auction && chown -R auction:auction /app
USER auction

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8501/ || exit 1

# Run application
CMD ["python", "-m", "streamlit", "run", "streamlit_app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

#### 2. Build and Run Container
```bash
# Build image
docker build -t auction-watcher .

# Run container
docker run -d \
  --name auction-watcher \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  auction-watcher
```

### Option 3: Cloud Deployment (Heroku)

#### 1. Prepare Heroku Files
Create `Procfile`:
```
web: streamlit run streamlit_app/app.py --server.port=$PORT --server.address=0.0.0.0
```

Create `runtime.txt`:
```
python-3.11.9
```

#### 2. Deploy to Heroku
```bash
# Install Heroku CLI and login
heroku login

# Create app
heroku create your-auction-watcher

# Set environment variables
heroku config:set LOG_LEVEL=INFO
heroku config:set SCRAPING_DELAY=3.0

# Deploy
git push heroku main
```

## 🔒 Security Considerations

### 1. Network Security
```bash
# Configure firewall (Linux)
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 8501/tcp   # Streamlit (if external access needed)
sudo ufw enable
```

### 2. SSL/TLS Setup (Production)
Use a reverse proxy like Nginx:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Rate Limiting
The application includes built-in rate limiting, but consider additional protection:

```bash
# Install fail2ban (Linux)
sudo apt-get install fail2ban

# Configure rate limiting for web scraping
# Edit /etc/fail2ban/jail.local
[nginx-req-limit]
enabled = true
filter = nginx-req-limit
action = iptables-multiport[name=ReqLimit, port="http,https", protocol=tcp]
logpath = /var/log/nginx/error.log
findtime = 600
bantime = 7200
maxretry = 10
```

## 📊 Monitoring & Maintenance

### 1. Log Monitoring
```bash
# Set up log rotation
sudo nano /etc/logrotate.d/auction-watcher

/opt/auction-watcher/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

### 2. Health Checks
Create `scripts/health_check.py`:

```python
#!/usr/bin/env python3
import requests
import sys
import os

def check_health():
    try:
        # Check web interface
        response = requests.get('http://localhost:8501', timeout=10)
        if response.status_code != 200:
            print(f"Dashboard health check failed: {response.status_code}")
            return False

        # Check ADOR connectivity
        response = requests.get('https://www.revenue.alabama.gov', timeout=10)
        if response.status_code != 200:
            print(f"ADOR connectivity check failed: {response.status_code}")
            return False

        print("All health checks passed")
        return True

    except Exception as e:
        print(f"Health check failed: {e}")
        return False

if __name__ == "__main__":
    if not check_health():
        sys.exit(1)
```

### 3. Automated Data Collection
Set up cron jobs for regular data collection:

```bash
# Edit crontab
crontab -e

# Add scheduled scraping (run daily at 6 AM)
0 6 * * * cd /opt/auction-watcher && python scripts/parser.py --scrape-county Mobile --max-pages 10 >> logs/scheduled_scraping.log 2>&1

# Health check every 15 minutes
*/15 * * * * cd /opt/auction-watcher && python scripts/health_check.py >> logs/health_check.log 2>&1
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# Verify Python path
python -c "import sys; print(sys.path)"

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### 2. Web Scraping Failures
```bash
# Test ADOR connectivity
curl -I https://www.revenue.alabama.gov

# Check rate limiting
python scripts/parser.py --scrape-county Baldwin --max-pages 1
```

#### 3. Dashboard Won't Start
```bash
# Check port availability
netstat -tlnp | grep 8501

# Start with explicit configuration
python -m streamlit run streamlit_app/app.py --server.port=8502
```

#### 4. Permission Issues
```bash
# Fix file permissions
sudo chown -R auction-watcher:auction-watcher /opt/auction-watcher
sudo chmod +x scripts/*.py
```

## 📈 Performance Optimization

### 1. Database Optimization (Optional)
For large-scale deployments, consider using a database:

```python
# config/database.py
import sqlite3
import pandas as pd

class PropertyDatabase:
    def __init__(self, db_path="data/properties.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY,
                parcel_id TEXT UNIQUE,
                county TEXT,
                amount REAL,
                acreage REAL,
                description TEXT,
                scraped_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
```

### 2. Caching Strategy
```python
# Add to streamlit_app/app.py
import streamlit as st

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_county_data(county):
    return pd.read_csv(f"data/processed/{county}_watchlist.csv")
```

### 3. Memory Management
```bash
# Monitor memory usage
free -h
top -p $(pgrep -f "streamlit")

# Set memory limits for Docker
docker run -m 2g auction-watcher
```

## 🎯 Production Checklist

- [ ] Python 3.10+ installed
- [ ] All dependencies installed via requirements.txt
- [ ] Environment variables configured
- [ ] Logging directory created with proper permissions
- [ ] Health checks passing
- [ ] Firewall configured appropriately
- [ ] SSL/TLS certificates installed (if external access)
- [ ] Monitoring and log rotation configured
- [ ] Backup strategy implemented
- [ ] Documentation reviewed by operations team
- [ ] Disaster recovery plan documented

## 📞 Support

For deployment issues:

1. **Check logs**: `tail -f logs/auction_watcher.log`
2. **Verify configuration**: Review environment variables and settings
3. **Test connectivity**: Ensure ADOR website is accessible
4. **Review troubleshooting guide**: See TROUBLESHOOTING.md
5. **Check system resources**: Memory, disk space, network

## 🔄 Updates & Maintenance

### Regular Maintenance Tasks
- **Weekly**: Review logs for errors or performance issues
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Review and update filtering criteria
- **Annually**: Performance review and capacity planning

### Update Procedure
```bash
# 1. Backup current installation
tar -czf auction-watcher-backup-$(date +%Y%m%d).tar.gz /opt/auction-watcher

# 2. Pull latest changes
git pull origin main

# 3. Update dependencies
pip install -r requirements.txt --upgrade

# 4. Test in staging environment
python scripts/parser.py --scrape-county Baldwin --max-pages 1

# 5. Restart production service
sudo systemctl restart auction-watcher
```

---

**Last Updated**: September 2025
**Version**: 1.0
**Maintained By**: Alabama Auction Watcher Team