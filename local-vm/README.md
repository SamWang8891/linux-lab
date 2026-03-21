# Local VM — Offline Linux Lab

A self-contained VM image for students to practise Linux challenges locally.
No server, no containers, no Guacamole — just a VM with a built-in quiz web app.

## Building the VM Images

### Prerequisites

Install on your build machine:

```bash
# macOS
brew install packer qemu

# Ubuntu/Debian
sudo apt install -y packer qemu-system-x86 qemu-system-arm qemu-utils
```

### Build x86_64 (Intel/AMD — Windows, Intel Mac)

```bash
cd local-vm/packer

# Build QCOW2
packer build -var 'arch=amd64' -only='qemu.linux-lab' linux-lab.pkr.hcl

# Convert to VMDK + OVA
cd output-amd64
qemu-img convert -f qcow2 -O vmdk linux-lab.qcow2 linux-lab.vmdk
# OVA = OVF descriptor + VMDK, packed with tar:
cd .. && bash scripts/make_ova.sh output-amd64/linux-lab.vmdk amd64
```

### Build ARM64 (Apple Silicon M-series)

```bash
cd local-vm/packer

packer build -var 'arch=arm64' -only='qemu.linux-lab' linux-lab.pkr.hcl

# ARM users typically use UTM or QEMU directly — QCOW2 is the main format
# VMware Fusion for ARM also supports VMDK:
cd output-arm64
qemu-img convert -f qcow2 -O vmdk linux-lab.vmdk linux-lab.vmdk
```

### Output

After building, you'll have:

| File | Format | For |
|------|--------|-----|
| `linux-lab.qcow2` | QCOW2 | KVM, UTM (macOS), QEMU |
| `linux-lab.vmdk` | VMDK | VMware, VirtualBox |
| `linux-lab.ova` | OVA | VirtualBox (double-click import) |

## For Students

1. Download the VM image for your platform
2. Import into VirtualBox / VMware / UTM
3. Boot the VM — it auto-logs in as `user`
4. Firefox opens automatically at `http://localhost` with the quiz
5. Open a terminal (on the desktop) and start solving challenges!
6. **Reset progress**: click the 🔄 Reset button on the quiz page

### Default credentials
- Username: `user`
- Password: `user`
- sudo: yes (with password)

### VM Specs
- Debian 12 (Bookworm) + XFCE desktop
- 2 vCPU, 2GB RAM, 8GB disk (thin provisioned)
- Nginx serves the quiz app on port 80
