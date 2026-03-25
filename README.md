# 🐧 Linux Lab

Linux 基礎學習平台 — 學生透過瀏覽器操作自己的 Debian 虛擬機，完成 CTF 風格的 Linux 指令學習任務。

## 架構

```
[學生瀏覽器] → [Nginx :80] → [Flask Web App :5000] → 帳號管理 + 任務系統
                    ↓
            [Apache Guacamole :8080] → 遠端桌面 / 終端機
                    ↓
            [LXD Containers] → 每位學生一台隔離的 Debian 12 容器
```

**核心元件：**
- **Flask** — Web 介面、帳號管理、Email 驗證、任務檢查
- **Apache Guacamole** — 瀏覽器內的 SSH / 遠端桌面（Docker 部署）
- **LXD** — 輕量級容器，每位學生獨立一台 Debian 12
- **Nginx** — 反向代理，統一入口
- **PostgreSQL** — Guacamole 後端資料庫（Docker 內）

## 快速安裝

### 前置需求

- Ubuntu 22.04+ 伺服器
- Docker & Docker Compose
- 至少 4GB RAM（每個學生容器約 256MB）

### 一鍵安裝

```bash
git clone https://github.com/your-org/gdg-thm.git
cd gdg-thm

# 複製並編輯環境變數
cp .env.example .env
nano .env  # 設定 SECRET_KEY、ADMIN_PASSWORD、SMTP 等

# 執行安裝腳本
sudo bash setup.sh
```

`setup.sh` 會自動完成：
- 安裝系統套件（python3、nginx、iptables 等）
- 設定 LXD 網路（`lab-net`, `10.99.0.0/24`）和 Profile
- 啟動 Guacamole（Docker Compose）
- 建立 Python 虛擬環境並安裝依賴
- 設定 Nginx 反向代理
- 建立 systemd 服務（`linux-lab`）
- 設定容器網路隔離和安全規則

安裝完成後：
- Web 介面：`http://your-server`
- 管理員帳號：`.env` 中的 `ADMIN_EMAIL` / `ADMIN_PASSWORD`

### 環境變數 (.env)

| 變數 | 說明 |
|------|------|
| `SECRET_KEY` | Flask session 密鑰 |
| `ADMIN_EMAIL` | 管理員 Email |
| `ADMIN_PASSWORD` | 管理員密碼 |
| `SITE_URL` | 網站公開 URL |
| `GUAC_URL` | Guacamole 內部 API 位址 |
| `GUAC_DB_PASS` | Guacamole 資料庫密碼 |
| `MAIL_SERVER` / `MAIL_PORT` | SMTP 伺服器設定 |
| `MAIL_USERNAME` / `MAIL_PASSWORD` | SMTP 認證 |

完整範本見 `.env.example`。

## 功能

### 👨‍💼 管理員
- Email 白名單管理（控制誰能註冊）
- 系統資源監控（CPU / RAM / Disk）
- 查看所有學生的容器狀態和答題進度
- 重置學生容器
- 網路設定管理

### 👩‍💻 學生
- 用白名單 Email 註冊（Email 驗證碼）
- 透過 Guacamole 在瀏覽器內操作 Debian 終端機
- 完成 23 道由易到難的學習任務
- 查看自己的容器狀態、自行重置容器

### 📚 學習任務（23 題）

| # | 任務 | # | 任務 |
|---|------|---|------|
| 1 | 查看指令手冊 | 13 | 建立軟連結 |
| 2 | 我是誰？ | 14 | 使用 curl 查看 HTTP 標頭 |
| 3 | 查看使用者所屬群組 | 15 | DNS 查詢 |
| 4 | 列出當前工作目錄 | 16 | 查看連接埠監聽狀態 |
| 5 | 列出檔案 | 17 | 壓縮與解壓縮 |
| 6 | 查看作業系統資訊 | 18 | 修改檔案權限 |
| 7 | 編輯檔案 | 19 | 修改檔案擁有者 |
| 8 | 建立資料夾 | 20 | 執行腳本 |
| 9 | 刪除檔案與資料夾 | 21 | 安裝並管理服務 |
| 10 | 複製檔案與資料夾 | 22 | 下載並安裝 .deb 套件 |
| 11 | 移動與重新命名檔案 | 23 | 修改 .bashrc |
| 12 | 尋找檔案 | | |

## 網路安全

- **容器隔離** — 學生容器之間的流量被 iptables 阻擋，無法互相通訊
- **Host 保護** — 容器僅允許 DNS 和 DHCP 流量到 Host，其餘全部 DROP
- **Metadata 阻擋** — 容器無法存取 `169.254.169.254`（雲端 metadata service）
- **規則持久化** — iptables 規則透過 systemd 服務在重開機後自動恢復

## 服務管理

```bash
# 查看狀態
systemctl status linux-lab

# 重啟
systemctl restart linux-lab

# 查看 Log
journalctl -u linux-lab -f

# 停止所有服務
systemctl stop linux-lab
docker compose -f docker-compose.guac.yml down
```

## 重置（Nuclear Reset）

如果需要清除所有資料重新來過：

```bash
sudo bash scripts/nuke.sh
```

這會刪除所有學生容器、LXD 設定、iptables 規則和資料庫。

## Local VM（離線模式）

不需要伺服器？`local-vm/` 提供獨立的 VirtualBox 虛擬機映像檔，學生可以在自己的電腦上離線練習。

詳見 [`local-vm/README.md`](local-vm/README.md)。

## 技術細節

- **框架：** Flask + SQLAlchemy + Flask-Login
- **容器：** LXD（Debian 12 映像檔，每容器限制 1 CPU 核心）
- **遠端存取：** Apache Guacamole（guacd 使用 host network 模式以存取 LXD 網段）
- **部署：** Gunicorn（4 workers）+ Nginx 反向代理
- **任務檢查：** 透過 SSH（Paramiko）連入容器自動驗證答案

## License

MIT
