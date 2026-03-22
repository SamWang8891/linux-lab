# 💻 Local VM (Offline Linux Lab)

這是一個獨立的虛擬機映像檔，讓學生可以在沒有伺服器的情況下，在自己的電腦上練習 Linux 指令。
虛擬機啟動後會自動開啟瀏覽器顯示任務系統，並與本機終端機互動。

---

## 🛠 建置準備 (Prerequisites)

你需要：
- [VirtualBox](https://www.virtualbox.org/wiki/Downloads) (macOS / Windows 都有)
- [Debian 12 netinst ISO](https://cdimage.debian.org/cdimage/archive/12.10.0/) (選擇你的架構：amd64 或 arm64)
- 本 repo 的 `local-vm/` 資料夾

### 格式轉換工具 (可選)
```bash
# macOS
brew install qemu  # 提供 qemu-img

# Windows
# 安裝 QEMU for Windows: https://qemu.weilnetz.de/w64/
# 或用 WSL: sudo apt install qemu-utils
```

---

## 🏗 建置步驟

### Step 1: 在 VirtualBox 建立 VM

1. 開啟 VirtualBox → 新增 (New)
2. 設定：
   - **名稱:** `Linux Lab`
   - **類型:** Linux → Debian (64-bit)
   - **記憶體:** 2048 MB
   - **硬碟:** 建立新虛擬硬碟 → VDI → 動態配置 → 8 GB
3. 掛載 Debian 12 netinst ISO 並啟動 VM
4. 安裝 Debian：
   - 選擇 **Install** (不要用 graphical install，省資源)
   - 語言/地區隨意
   - Hostname: `linux-lab`
   - Root 密碼: 設一個 (稍後會鎖定)
   - 使用者: `user` / 密碼: `user`
   - 分割區: 使用整個磁碟 → 全部放在一個分區
   - 軟體選擇: **只勾 SSH server 和 standard system utilities** (桌面環境由 setup.sh 安裝)
5. 安裝完成後重新開機

### Step 2: 複製檔案到 VM 並執行 setup

```bash
# 從你的主機，用 scp 把 local-vm/ 和主專案檔案複製進去
# (先在 VirtualBox 設定 Port Forwarding: Host 2222 → Guest 22)

# 複製整個專案 (setup.sh 需要上層的 templates/, static/ 等)
scp -P 2222 -r gdg-thm/ user@localhost:~/

# SSH 進去
ssh -p 2222 user@localhost

# 在 VM 內執行
cd ~/gdg-thm/local-vm
sudo bash setup.sh
```

### Step 3: 測試

1. 重新開機: `sudo reboot`
2. VM 應該會自動登入 XFCE 桌面
3. Firefox 自動開啟 `http://localhost` (練習介面)
4. Terminal 自動開啟
5. 確認一切正常後 → 關機 (shutdown)

### Step 4: 清理並匯出

```bash
# 在 VM 內，關機前清理
sudo apt-get clean
sudo rm -rf /var/lib/apt/lists/* ~/gdg-thm
history -c
sudo su -c "history -c"
sudo shutdown -h now
```

---

## 📦 匯出與轉換

### 匯出 OVA (通用格式 — VirtualBox / VMware / Parallels 都能用)
```bash
VBoxManage export "Linux Lab" -o linux-lab.ova
```

### 轉換成 QCOW2 (給 UTM / QEMU / KVM)
```bash
# 先找到 VDI 檔案路徑
# macOS: ~/VirtualBox VMs/Linux Lab/Linux Lab.vdi
# Windows: C:\Users\<你>\VirtualBox VMs\Linux Lab\Linux Lab.vdi

qemu-img convert -f vdi -O qcow2 "Linux Lab.vdi" linux-lab.qcow2
```

---

## 📁 最終產出檔案

| 檔案 | 格式 | 適用平台 |
|------|------|----------|
| `linux-lab.ova` | OVA | VirtualBox, VMware Fusion, VMware Workstation, Parallels |
| `linux-lab.qcow2` | QCOW2 | UTM (macOS), QEMU, KVM (Linux) |

**OVA 一個檔案搞定** — 包含 VM 設定 + 磁碟映像，雙擊即可匯入。

---

## 🎓 學生使用指南 (For Students)

1. 下載對應你電腦的虛擬機映像檔
2. **VirtualBox / VMware / Parallels:** 雙擊 `.ova` 檔匯入
3. **UTM (macOS):** 匯入 `.qcow2` 檔
4. 啟動虛擬機 — 系統會自動以 `user` 帳號登入
5. **Firefox** 會自動開啟並載入 `http://localhost` (練習介面)
6. 開啟桌面上的 **Terminal** (終端機) 開始挑戰！

### 預設帳號密碼
- **帳號:** `user`
- **密碼:** `user`
- **權限:** 支援 `sudo` (需輸入密碼 `user`)

### 虛擬機規格
- **OS:** Debian 12 (Bookworm) + XFCE 桌面環境
- **資源:** 2 vCPU, 2GB RAM, 8GB Disk
- **重置進度:** 點選練習介面上的 🔄 **Reset** 按鈕即可清除進度
