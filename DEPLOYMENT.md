# 🚀 Production Deployment Guide

## Webhook-Based Bot Deployment

This guide covers deploying the Metropolitan Expo Attendance Bot on a production server using webhooks for 24/7 operation.

## 📋 Prerequisites

- **Linux server** (Ubuntu 20.04+ recommended)
- **Domain name** with SSL certificate
- **Python 3.8+** installed
- **Supervisor** or **systemd** for process management
- **Nginx** for reverse proxy (optional but recommended)

## 🔧 Environment Variables

Create a `.env` file on your server:

```bash
# Telegram Bot
TELEGRAM_TOKEN=your_bot_token_here
BOT_USERNAME=your_bot_username

# Webhook Configuration
WEBHOOK_URL=https://yourdomain.com
WEBHOOK_PORT=8443
WEBHOOK_PATH=/webhook
WEBHOOK_SECRET=your_secret_token_here

# Google Sheets
SPREADSHEET_ID=your_spreadsheet_id
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# Office Location
OFFICE_LATITUDE=37.956194
OFFICE_LONGITUDE=23.957333
OFFICE_RADIUS_METERS=100
```

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo>
cd metrpolitanbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. SSL Certificate (Required for HTTPS)

```bash
# Using Let's Encrypt
sudo apt install certbot
sudo certbot certonly --standalone -d yourdomain.com

# Or use your own certificates
# Place cert.pem and key.pem in your project directory
```

### 3. Update SSL Paths

Edit `attendance_bot.py` and uncomment SSL lines:

```python
ssl_context.load_cert_chain('/etc/letsencrypt/live/yourdomain.com/cert.pem', 
                           '/etc/letsencrypt/live/yourdomain.com/privkey.pem')
```

### 4. Test Run

```bash
python3 attendance_bot.py
```

## 🐧 Production Setup with Supervisor

### 1. Install Supervisor

```bash
sudo apt install supervisor
```

### 2. Create Config File

```bash
sudo nano /etc/supervisor/conf.d/metropolitan-bot.conf
```

Add this content:

```ini
[program:metropolitan-bot]
command=/path/to/your/project/venv/bin/python /path/to/your/project/attendance_bot.py
directory=/path/to/your/project
user=your_user
autostart=true
autorestart=true
stderr_logfile=/var/log/metropolitan-bot.err.log
stdout_logfile=/var/log/metropolitan-bot.out.log
environment=HOME="/path/to/your/project"
```

### 3. Start Service

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start metropolitan-bot
sudo supervisorctl status metropolitan-bot
```

## 🌐 Nginx Reverse Proxy (Recommended)

### 1. Install Nginx

```bash
sudo apt install nginx
```

### 2. Create Site Config

```bash
sudo nano /etc/nginx/sites-available/metropolitan-bot
```

Add this content:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    location /webhook/ {
        proxy_pass http://127.0.0.1:8443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location / {
        return 404;
    }
}
```

### 3. Enable Site

```bash
sudo ln -s /etc/nginx/sites-available/metropolitan-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 🔒 Security Considerations

### 1. Firewall Setup

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. Bot Token Security

- Never commit bot tokens to version control
- Use environment variables
- Rotate tokens regularly
- Monitor bot access logs

### 3. Webhook Security

- Use HTTPS only in production
- Implement webhook secret validation
- Rate limiting (implement in your webhook handler)
- Monitor webhook endpoints

## 📊 Monitoring

### 1. Log Monitoring

```bash
# View bot logs
tail -f logs/bot.log

# View supervisor logs
sudo supervisorctl tail metropolitan-bot

# View nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 2. Health Check

Create a simple health check endpoint:

```python
# Add to your webhook handler
@app.router.add_get('/health')
async def health_check(request):
    return web.Response(text='OK', status=200)
```

## 🚨 Troubleshooting

### Common Issues:

1. **Webhook not receiving updates**
   - Check SSL certificate validity
   - Verify webhook URL is accessible
   - Check bot token in webhook URL

2. **Permission denied errors**
   - Ensure proper file permissions
   - Check user permissions for SSL certificates

3. **Port already in use**
   - Change webhook port in config
   - Check if another service is using the port

### Debug Mode:

```bash
# Run with debug logging
export LOG_LEVEL=DEBUG
python3 attendance_bot.py
```

## 🔄 Updates and Maintenance

### 1. Update Bot

```bash
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo supervisorctl restart metropolitan-bot
```

### 2. SSL Renewal

```bash
# Add to crontab for auto-renewal
0 12 * * * /usr/bin/certbot renew --quiet
```

## 📈 Performance Tips

- Use **gunicorn** for multiple worker processes
- Implement **Redis** for session storage
- Use **CDN** for static assets
- Monitor **memory usage** and **response times**

## 🆘 Support

For deployment issues:
1. Check logs first
2. Verify environment variables
3. Test webhook endpoint manually
4. Check Telegram Bot API status

---

**🎯 Your bot is now ready for 24/7 production operation with webhooks!**
