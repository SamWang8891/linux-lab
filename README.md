# 🐧 Linux Lab

Linux 基礎學習平台，讓學生透過瀏覽器操作自己的 Debian 虛擬機並完成 CTF 風格的學習任務。

## 架構

```
[學生瀏覽器] → [Flask Web Portal :5000] → 帳號管理 + 任務系統
                    ↓
            [Apache Guacamole :8080] → 遠端桌面/終端機
                    ↓
            [LXD Containers] → 每個學生一台 Debian 12 虛擬機
```

## 安裝步驟

### 1. 安裝 LXD
```bash
sudo snap install lxd
sudo lxd init --minimal
sudo usermod -aG lxd $USER
# 重新登入讓群組生效
```

### 2. 設定 LXD 網路和 Profile
```bash
sudo bash scripts/setup_lxd.sh
```

### 3. 安裝 Guacamole (Docker Compose)
```bash
# 複製環境變數範本並修改
cp .env.example .env
nano .env

# 產生 DB schema + 啟動
bash scripts/setup_guac_db.sh
```

**重要：** guacd 需要能連到 LXD 容器 (10.99.0.0/24)。
如果 Docker 預設 bridge 不能路由到 LXD 網段，改用 host network：
```bash
# 在 docker-compose.guac.yml 中，guacd service 加上：
# network_mode: host
```

### 4. 安裝 Flask App
```bash
cd linux-lab
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 設定環境變數
export SECRET_KEY="your-random-secret"
export GUAC_URL="http://localhost:8080/guacamole"
export ADMIN_EMAIL="admin@example.com"
export ADMIN_PASSWORD="your-admin-password"
export MAIL_SERVER="smtp.example.com"
export MAIL_USERNAME="lab@example.com"
export MAIL_PASSWORD="smtp-password"

# 啟動
python app.py
```

### 5. 正式部署
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

建議前面再加 nginx 做 reverse proxy + HTTPS。

## 功能

### 管理員
- 管理 Email 白名單
- 監控系統資源 (CPU/RAM/Disk)
- 查看每個學生的機器狀態和答題進度
- 重置學生機器

### 學生
- 用白名單中的 Email 註冊
- 透過 Guacamole 連線到自己的 Debian 機器（桌面 or 終端機）
- 完成 14 道 Linux 學習任務
- 查看機器狀態、重置機器

### 學習任務（由易到難）
1. whoami / id
2. ls（含隱藏檔案）
3. find 尋找檔案
4. 查看 OS 資訊
5. unzip / tar 解壓縮
6. chmod + 執行檔案
7. rm 刪除檔案
8. 查看檔案權限
9. nano/vim 編輯檔案
10. 修改 .bashrc
11. ss/netstat 列出連接埠
12. apt install + systemctl（nginx）
13. dpkg -i 安裝 .deb
14. 更改密碼

## 網路隔離

學生容器之間互相無法通訊（iptables 阻擋）。
Host 可以存取每個容器的 port 22 (SSH) 和 port 80 (HTTP)，用於自動檢查任務完成狀態。
