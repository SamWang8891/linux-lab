# 🐧 Linux Lab

一個 CTF 風格的 Linux 基礎學習平台。學生透過瀏覽器連線到自己專屬的 Debian 容器，完成 23 道由淺入深的實作任務。

## 功能特色

- **每人一台獨立環境** — 基於 LXD 容器，互相隔離
- **瀏覽器操作** — 透過 Apache Guacamole 提供 Web 終端機
- **23 道學習任務** — 從 `man` 指令到安裝服務，循序漸進
- **自動答案驗證** — 系統透過 SSH 連進容器即時檢查
- **管理員儀表板** — 查看全班進度、系統資源、重置容器
- **Email 白名單註冊** — 限制存取範圍
- **一鍵部署** — `setup.sh` 自動搞定所有設定

## 架構

```
瀏覽器 → Nginx (:80) ─┬─ Flask App (:5000) → 帳號管理 + 任務驗證
                       │                          ↓
                       └─ Guacamole (:8080) → Web 終端機
                                                   ↓
                                          LXD 容器 (Debian 12)
                                          每位學生一台，網路互相隔離
```

## 學習任務

| # | 任務 | # | 任務 |
|---|------|---|------|
| 1 | 查看指令手冊 | 13 | 建立軟連結 |
| 2 | 我是誰？ | 14 | 使用 curl 查看 HTTP 標頭 |
| 3 | 查看使用者群組 | 15 | DNS 查詢 |
| 4 | 列出當前工作目錄 | 16 | 查看連接埠監聽狀態 |
| 5 | 列出檔案 | 17 | 壓縮與解壓縮 |
| 6 | 查看作業系統資訊 | 18 | 修改檔案權限 |
| 7 | 編輯檔案 | 19 | 修改檔案擁有者 |
| 8 | 建立資料夾 | 20 | 執行腳本 |
| 9 | 刪除檔案與資料夾 | 21 | 安裝並管理服務 |
| 10 | 複製檔案與資料夾 | 22 | 下載並安裝 .deb 套件 |
| 11 | 移動與重新命名檔案 | 23 | 修改 .bashrc |
| 12 | 尋找檔案 | | |

## 系統需求

- Ubuntu 22.04+ (建議)
- Docker + Docker Compose
- LXD (snap)
- Python 3.10+
- Nginx
- 至少 2GB RAM + 每位學生約 512MB

## 快速開始

```bash
# 1. 複製並編輯環境變數
cp .env.example .env
nano .env    # 填入 SECRET_KEY、ADMIN_PASSWORD、MAIL 等設定

# 2. 一鍵安裝
sudo bash setup.sh
```

完成後：
- **Web 介面：** `http://your-server-ip`
- **管理員帳號：** 見 `.env` 中的 `ADMIN_EMAIL` / `ADMIN_PASSWORD`

### 手動安裝

如果你想逐步設定：

```bash
# LXD 網路和 Profile
sudo bash scripts/setup_lxd.sh

# Guacamole (Docker Compose)
bash scripts/setup_guac_db.sh

# Python 環境
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 啟動
gunicorn -w 4 -b 127.0.0.1:5000 app:app
```

## 環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `SECRET_KEY` | Flask session 金鑰 | *(必填)* |
| `ADMIN_EMAIL` | 管理員 Email | `admin@example.com` |
| `ADMIN_PASSWORD` | 管理員密碼 | *(必填)* |
| `SITE_URL` | 網站網址 | `http://your-server-ip` |
| `GUAC_URL` | Guacamole 內部 API | `http://localhost:8080/guacamole` |
| `GUAC_PUBLIC_URL` | Guacamole 對外路徑 | `/guacamole` |
| `GUAC_ADMIN_USER` | Guacamole 管理員帳號 | `guacadmin` |
| `GUAC_ADMIN_PASS` | Guacamole 管理員密碼 | `guacadmin` |
| `GUAC_DB_PASS` | Guacamole 資料庫密碼 | *(建議修改)* |
| `MAIL_SERVER` | SMTP 伺服器 | *(必填)* |
| `MAIL_PORT` | SMTP 連接埠 | `465` |
| `MAIL_USERNAME` | SMTP 帳號 | *(必填)* |
| `MAIL_PASSWORD` | SMTP 密碼 | *(必填)* |
| `MAIL_SENDER` | 寄件者 Email | *(必填)* |
| `LXD_NETWORK` | LXD 網路名稱 | `lab-net` |
| `LXD_PROFILE` | LXD Profile 名稱 | `lab-student` |
| `LXD_IMAGE` | LXD 容器映像檔 | `images:debian/12` |

完整範例見 [`.env.example`](.env.example)。

## 網路安全

- 學生容器之間 **互相隔離**（iptables 阻擋）
- 容器 **無法存取主機服務**（僅 DNS/DHCP 放行）
- Metadata endpoint (`169.254.169.254`) 被封鎖
- 主機透過 SSH 連入容器驗證任務（port 22）

## 離線版本（Local VM）

提供 VirtualBox / UTM 虛擬機映像，讓學生在沒有伺服器的情況下，於自己電腦上練習。

詳見 [`local-vm/README.md`](local-vm/README.md)。

## 維護指令

```bash
# 服務管理
systemctl status linux-lab
systemctl restart linux-lab
journalctl -u linux-lab -f

# 核爆重置（刪除所有容器和設定，重頭來過）
sudo bash scripts/nuke.sh
```

## 技術元件

- **後端：** Flask + SQLAlchemy + Flask-Login
- **遠端桌面：** Apache Guacamole (Docker)
- **容器：** LXD (Debian 12)
- **反向代理：** Nginx
- **驗證：** Paramiko (SSH) 即時檢查任務
