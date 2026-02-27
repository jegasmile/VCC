#!/bin/bash

apt update -y
apt install -y python3
mkdir -p /var/www/html

cat <<EOF > /var/www/html/index.html
<!DOCTYPE html>
<html>
<head>
    <title>GCP Debian 12 Web Server</title>
    <style>
        body {
            font-family: Arial;
            text-align: center;
            margin-top: 50px;
            background-color: #f4f4f4;
        }
        h1 { color: #2c3e50; }
    </style>
</head>
<body>
    <h1>VCC Assignment VM Running Successfully  on GCP</h1>
    <p>This is Jegadeesh kumar</p>
    <p>Role no M25AI2106</p>
</body>
</html>
EOF

cd /var/www/html
nohup python3 -m http.server 80 &
