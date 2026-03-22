# 💻 Local VM (Offline Linux Lab)

這是一個獨立的虛擬機映像檔，讓學生可以在沒有伺服器的情況下，在自己的電腦上練習 Linux 指令。
虛擬機啟動後會自動開啟瀏覽器顯示任務系統，並與本機終端機互動。

## 🛠 準備建置環境 (Prerequisites)

在開始建置之前，請根據你的作業系統安裝必要工具：

### Ubuntu / Debian (建議)
```bash
sudo apt update
sudo apt install -y packer qemu-system-x86 qemu-system-arm qemu-utils genisoimage
```

### macOS (Intel or Apple Silicon)
```bash
brew tap hashicorp/tap
brew install hashicorp/tap/packer qemu

# Apple Silicon (M1/M2/M3/M4) 額外需求 (QEMU EFI Firmware)
# 如果 build 失敗，請確認 /opt/homebrew/share/qemu/ 下有 edk2-aarch64-code.fd
```

---

## 🏗 建置虛擬機映像檔 (Building the Images)

進入建置目錄：
```bash
cd gdg-thm/local-vm/packer
```

### 1. 建置 x86_64 (Intel / AMD / Windows / Intel Mac)
```bash
packer init .

# 建置 QCOW2 格式 (Debian 12 + XFCE)
packer build -var 'arch=amd64' linux-lab.pkr.hcl

# 轉換格式為 VMDK (給 VMware / VirtualBox)
qemu-img convert -f qcow2 -O vmdk output-amd64/linux-lab.qcow2 output-amd64/linux-lab.vmdk

# 打包成 OVA (VirtualBox 可直接匯入)
bash scripts/make_ova.sh output-amd64/linux-lab.vmdk amd64
```

### 2. 建置 ARM64 (Apple Silicon M1/M2/M3)
```bash
packer init .

# 建置 QCOW2 格式 (用於 UTM 或 QEMU)
packer build -var 'arch=arm64' linux-lab.pkr.hcl

# 如果需要 VMDK 格式 (給 VMware Fusion for ARM)
qemu-img convert -f qcow2 -O vmdk output-arm64/linux-lab.qcow2 output-arm64/linux-lab.vmdk
```

---

## 📁 產出檔案說明 (Output)

建置完成後，你可以在 `output-arch/` 資料夾找到以下檔案：

| 檔案名稱 | 格式 | 適用平台 |
|------|--------|-----|
| `linux-lab.qcow2` | QCOW2 | KVM, UTM (macOS), QEMU |
| `linux-lab.vmdk` | VMDK | VMware, VirtualBox |
| `linux-lab.ova` | OVA | VirtualBox (按兩下即可匯入) |

---

## 🎓 學生使用指南 (For Students)

1. 下載對應你電腦架構的虛擬機映像檔。
2. 匯入至虛擬機軟體 (VirtualBox / VMware / UTM)。
3. 啟動虛擬機 — 系統會自動以 `user` 帳號登入。
4. **Firefox** 會自動開啟並載入 `http://localhost` (練習介面)。
5. 開啟桌面上的 **Terminal** (終端機) 開始挑戰！

### 預設帳號密碼
- **帳號:** `user`
- **密碼:** `user`
- **權限:** 支援 `sudo` (需輸入密碼 `user`)

### 虛擬機規格
- **OS:** Debian 12 (Bookworm) + XFCE 桌面環境
- **資源:** 2 vCPU, 2GB RAM, 8GB Disk
- **重置進度:** 點選練習介面上的 🔄 **Reset** 按鈕即可清除進度。
