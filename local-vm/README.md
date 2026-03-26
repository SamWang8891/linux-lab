# 💻 Local VM (Offline Linux Lab)

獨立的虛擬機映像檔，讓學生在沒有伺服器的情況下，於自己電腦上練習 Linux 指令。
虛擬機啟動後會自動登入桌面、開啟瀏覽器顯示任務系統，搭配終端機完成挑戰。

---

## 🖥 虛擬機軟體一覽

### Windows (Intel / AMD)

| 軟體 | 免費 | 備註 |
|------|------|------|
| **VirtualBox** ⭐ | ✅ | 最簡單，直接匯入 OVA 即可使用。建議用 **BIOS 模式**建置的映像，避免 EFI 相關問題。 |
| **VMware Workstation** | ✅ (個人免費) | 效能好，但官網下載需要 [Broadcom 帳號](https://support.broadcom.com/)。GUI 匯出預設為多檔 OVF，無法直接匯出成單一 OVA 檔案，需用 `ovftool` 指令（見下方）。 |
| **QEMU** | ✅ | 開源、功能強大，但安裝和使用對初學者門檻較高，需熟悉命令列操作。使用 QCOW2 格式。 |

> ⚠️ **VirtualBox + EFI 注意事項：** VirtualBox 的 Snapshot 功能在使用 EFI 韌體的虛擬機上可能導致 EFI 開機設定損壞（已知 bug）。建議使用 **BIOS 模式**建置的映像，或避免使用 Snapshot。

### macOS

| 軟體 | 免費 | Intel Mac | Apple Silicon | 備註 |
|------|------|-----------|---------------|------|
| **VMware Fusion** ⭐ | ✅ (個人免費) | ✅ | ✅ | 推薦。效能好、相容性佳。官網下載需要 [Broadcom 帳號](https://support.broadcom.com/)。目前 GUI **沒有匯出功能**，需用 `ovftool` 指令匯出 OVA。 |
| **UTM** | ✅ | ✅ | ✅ (原生) | 開源、基於 QEMU。免費易用，Apple Silicon 上可原生虛擬化 ARM 系統。不支援直接匯入 OVA，需先轉為 QCOW2 格式（見下方）。App Store 版需付費，[GitHub 版](https://github.com/utmapp/UTM/releases)免費。 |
| **Parallels Desktop** | ❌ | ✅ | ✅ | 效能最好，但需要訂閱付費（或破解）。 |
| **VirtualBox** | ✅ | ✅ | ✅ (7.1+) | 免費，但 Snapshot 功能可能損壞 EFI 虛擬機的開機設定（見上方注意事項）。Apple Silicon 支援仍在開發中。 |

---

## 🛠 建置準備

你需要：
- **VMware Fusion** (macOS) 或 **VMware Workstation** (Windows)，或其他上述虛擬機軟體
- [Debian 12.10.0 netinst ISO](https://cdimage.debian.org/cdimage/archive/12.10.0/)（選擇對應架構：amd64 或 arm64）
- 本 repo 的 `local-vm/` 資料夾

### 格式轉換工具（可選）
```bash
# macOS
brew install qemu  # 提供 qemu-img

# Windows（擇一）
# 安裝 QEMU for Windows: https://qemu.weilnetz.de/w64/
# 或用 WSL: sudo apt install qemu-utils
```

---

## 🏗 建置步驟

### Step 1: 建立 VM

1. 在 VMware 中新增虛擬機
2. 設定：
   - **Guest OS:** Debian 12 (64-bit)
   - **記憶體:** 2048 MB
   - **硬碟:** 8 GB（動態配置）
   - **韌體:** 建議選擇 **BIOS**（非 UEFI），匯出後相容性最好
3. 掛載 Debian 12 netinst ISO 並啟動
4. 安裝 Debian：
   - 選擇 **Install**（不要用 graphical install，省資源）
   - Hostname: `linux-lab`
   - Root 密碼: 設一個（稍後會鎖定）
   - 使用者: `user` / 密碼: `user`
   - 分割區: 使用整個磁碟 → 全部放在一個分區
   - 軟體選擇: **只勾 SSH server 和 standard system utilities**（桌面環境由 setup.sh 安裝）
5. 安裝完成後重新開機

> 💡 **為什麼建議 BIOS？** OVA 匯出不會包含 NVRAM（EFI 變數儲存），導致 EFI 開機設定遺失。使用 BIOS 模式可以避免學生匯入後無法開機的問題。

### Step 2: 複製檔案到 VM 並執行 setup

```bash
# 從主機用 scp 複製檔案進 VM
# (先確認 VM 的 SSH 可連線，或設定 Port Forwarding)

scp -r gdg-thm/ user@<VM-IP>:~/

# SSH 進去
ssh user@<VM-IP>

# 在 VM 內執行
cd ~/gdg-thm/local-vm
sudo bash setup.sh
```

### Step 3: 測試

1. 重新開機: `sudo reboot`
2. VM 應自動登入 XFCE 桌面
3. Firefox 自動開啟 `http://localhost`（練習介面）
4. Terminal 自動開啟
5. 確認功能正常後 → 關機

### Step 4: 清理並準備匯出

```bash
# 在 VM 內，關機前清理
sudo apt-get clean
sudo rm -rf /var/lib/apt/lists/* ~/gdg-thm
history -c
sudo su -c "history -c"

# ⭐ 用 dd 寫入零值，匯出後壓縮效果會好很多
sudo dd if=/dev/zero of=/zero bs=1M 2>/dev/null; sudo rm -f /zero

sudo shutdown -h now
```

> 💡 `dd` 寫零的原理：虛擬磁碟中已刪除的區塊仍保留舊資料，填入零後 OVA 打包時壓縮率大幅提升，檔案會小很多。

---

## 📦 匯出 OVA

目前 VMware Fusion 的 GUI 沒有匯出選項，VMware Workstation 的 GUI 匯出只會產生多檔 OVF（而非單一 OVA）。兩者都可以用 `ovftool` 指令直接匯出成一個 `.ova` 檔案：

### macOS (VMware Fusion)

```bash
# ovftool 隨 Fusion 一起安裝
"/Applications/VMware Fusion.app/Contents/Library/VMware OVF Tool/ovftool" \
  --acceptAllEulas \
  ~/Virtual\ Machines.localized/Linux\ Lab.vmwarevm/Linux\ Lab.vmx \
  ~/Desktop/linux-lab.ova
```

### Windows (VMware Workstation)

```cmd
:: ovftool 隨 Workstation 一起安裝
"C:\Program Files\VMware\VMware Workstation\OVFTool\ovftool.exe" ^
  --acceptAllEulas ^
  "C:\Users\<你的使用者>\Documents\Virtual Machines\Linux Lab\Linux Lab.vmx" ^
  "C:\Users\<你的使用者>\Desktop\linux-lab.ova"
```

> 路徑請依實際 VM 位置調整。`ovftool` 會將所有檔案打包成單一 `.ova`。

---

## 🔧 EFI 修復指南

如果你使用了 **EFI/UEFI 模式**建置的映像，學生匯入後可能會遇到無法開機的問題（因為 NVRAM 不包含在 OVA 中）。以下是修復步驟：

### Windows (Intel / AMD CPU)

1. 匯入 OVA 檔案後，開啟虛擬機
2. 虛擬機開機時，立刻按下 **F2**（可能需要搭配 **Fn** 鍵）
3. 用方向鍵選取 **EFI Internal Shell**，按 Enter
4. 輸入以下指令開機：
   ```
   fs0:\EFI\debian\grubx64.efi
   ```
5. 成功開機後，打開終端機，執行以下指令永久修復：
   ```bash
   sudo grub-install
   ```

### macOS (M Series / Intel Mac)

1. 匯入 OVA 檔案後，找到 VM 的 `.vmx` 設定檔
2. 編輯 `.vmx`，找到 `guestOS`，將值改為 `arm-debian12-64`，存檔
3. 開啟虛擬機，開機時立刻按下 **F2**（可能需要搭配 **Fn** 鍵）
4. 用方向鍵選取 **EFI Internal Shell**，按 Enter
5. 輸入以下指令開機：
   ```
   fs0:\EFI\debian\grubaa64.efi
   ```
6. 成功開機後，打開終端機，執行以下指令永久修復：
   ```bash
   sudo grub-install
   ```

---

## 🔄 轉換為 QCOW2（給 UTM / QEMU）

如果學生使用 UTM 或 QEMU，需要將 OVA 中的 VMDK 轉為 QCOW2 格式：

```bash
# 1. 解開 OVA（它其實是個 tar 檔）
tar xvf linux-lab.ova

# 2. 將解出的 VMDK 轉為 QCOW2
qemu-img convert -f vmdk -O qcow2 disk.vmdk disk.qcow2
```

然後在 UTM 中新增虛擬機，選擇「Emulate」或「Virtualize」，掛載 `disk.qcow2` 作為磁碟即可。

> ⚠️ 使用 arm64 架構的 OVA 在轉換後，可能需要參照上方的 **EFI 修復步驟**。

---

## 📁 最終產出檔案

| 檔案 | 格式 | 適用平台 |
|------|------|----------|
| `linux-lab.ova` | OVA | VMware Fusion, VMware Workstation, VirtualBox, Parallels |
| `linux-lab.qcow2` | QCOW2 | UTM (macOS/iOS), QEMU, KVM (Linux) |

---

## 🎓 學生使用指南

1. 下載對應你電腦的虛擬機映像檔
2. **VMware / VirtualBox / Parallels:** 雙擊 `.ova` 檔匯入
3. **UTM:** 需先轉為 `.qcow2`（見上方說明），或直接下載 QCOW2 版本
4. 啟動虛擬機 — 系統會自動登入桌面
5. **Firefox** 自動開啟 `http://localhost`（練習介面）
6. 開啟桌面上的 **Terminal** 開始挑戰！

### 預設帳號密碼
- **帳號:** `user`
- **密碼:** `user`
- **權限:** 支援 `sudo`（需輸入密碼 `user`）

### 虛擬機規格
- **OS:** Debian 12 (Bookworm) + XFCE 桌面環境
- **資源:** 2 vCPU, 2GB RAM, 8GB Disk
- **重置進度:** 點選練習介面上的 🔄 **Reset** 按鈕即可清除進度
