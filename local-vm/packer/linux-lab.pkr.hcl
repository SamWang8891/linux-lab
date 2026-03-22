packer {
  required_plugins {
    qemu = {
      source  = "github.com/hashicorp/qemu"
      version = "~> 1"
    }
  }
}

variable "arch" {
  type    = string
  default = "amd64"
  validation {
    condition     = contains(["amd64", "arm64"], var.arch)
    error_message = "Arch must be amd64 or arm64."
  }
}

locals {
  iso_url_amd64    = "https://cdimage.debian.org/cdimage/archive/12.10.0/amd64/iso-cd/debian-12.10.0-amd64-netinst.iso"
  iso_sha_amd64    = "file:https://cdimage.debian.org/cdimage/archive/12.10.0/amd64/iso-cd/SHA256SUMS"
  qemu_bin_amd64   = "qemu-system-x86_64"
  machine_amd64    = "q35"

  iso_url_arm64    = "https://cdimage.debian.org/cdimage/archive/12.10.0/arm64/iso-cd/debian-12.10.0-arm64-netinst.iso"
  iso_sha_arm64    = "file:https://cdimage.debian.org/cdimage/archive/12.10.0/arm64/iso-cd/SHA256SUMS"
  qemu_bin_arm64   = "qemu-system-aarch64"
  machine_arm64    = "virt"

  iso_url   = var.arch == "amd64" ? local.iso_url_amd64 : local.iso_url_arm64
  iso_sha   = var.arch == "amd64" ? local.iso_sha_amd64 : local.iso_sha_arm64
  qemu_bin  = var.arch == "amd64" ? local.qemu_bin_amd64 : local.qemu_bin_arm64
  machine   = var.arch == "amd64" ? local.machine_amd64 : local.machine_arm64
}

source "qemu" "linux-lab" {
  iso_url          = local.iso_url
  iso_checksum     = local.iso_sha
  output_directory = "output-${var.arch}"
  vm_name          = "linux-lab.qcow2"
  format           = "qcow2"
  disk_size        = "8G"
  disk_compression = true

  qemuargs = var.arch == "arm64" ? [
    ["-machine", "virt"],
    ["-cpu", "cortex-a72"],
    ["-bios", "/usr/share/qemu-efi-aarch64/QEMU_EFI.fd"],
  ] : []

  accelerator      = "kvm"
  cpus             = 2
  memory           = 2048
  headless         = true
  qemu_binary      = local.qemu_bin

  http_directory   = "http"
  boot_wait        = "5s"
  boot_command     = var.arch == "amd64" ? [
    "<esc><wait>",
    "auto url=http://{{ .HTTPIP }}:{{ .HTTPPort }}/preseed.cfg ",
    "hostname=linux-lab domain= ",
    "<enter>"
  ] : [
    "auto url=http://{{ .HTTPIP }}:{{ .HTTPPort }}/preseed.cfg ",
    "hostname=linux-lab domain= ",
    "<enter>"
  ]

  ssh_username     = "root"
  ssh_password     = "packer-build"
  ssh_timeout      = "30m"
  shutdown_command  = "shutdown -P now"
}

build {
  sources = ["source.qemu.linux-lab"]

  # Copy the main app files into the VM
  provisioner "file" {
    source      = "../../app.py"
    destination = "/opt/linux-lab/app_local.py"
  }

  provisioner "file" {
    source      = "../../models.py"
    destination = "/opt/linux-lab/models.py"
  }

  provisioner "file" {
    source      = "../../config.py"
    destination = "/opt/linux-lab/config.py"
  }

  provisioner "file" {
    source      = "../../quiz_checker.py"
    destination = "/opt/linux-lab/quiz_checker.py"
  }

  provisioner "file" {
    source      = "../../challenges.json"
    destination = "/opt/linux-lab/challenges.json"
  }

  provisioner "file" {
    source      = "../../templates/"
    destination = "/opt/linux-lab/templates/"
  }

  provisioner "file" {
    source      = "../../static/"
    destination = "/opt/linux-lab/static/"
  }

  provisioner "file" {
    source      = "../nginx/linux-lab.conf"
    destination = "/tmp/linux-lab-nginx.conf"
  }

  # Run the provisioning script
  provisioner "shell" {
    script = "scripts/provision.sh"
  }
}
