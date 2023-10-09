resource "proxmox_virtual_environment_container" "service1" {
  description = "Managed by Terraform"

  node_name = var.PROXMOX_NODE

  count = var.TEAM_COUNT

  vm_id     = 1000 + count

  initialization {
    hostname = "team${count}-service1"

    ip_config {
      ipv4 {
        address = "192.168.${count}.1/24"
        gateway = "192.168.${count}.254"
      }
    }

    user_account {
      keys = [
        trimspace(tls_private_key.ubuntu_container_key.public_key_openssh)
      ]
      password = random_password.ubuntu_container_password.result
    }
  }

  network_interface {
    name = "veth0"
    bridge = "vmbrteam${count}"
  }

  operating_system {
    template_file_id = proxmox_virtual_environment_file.ubuntu_container_template.id
    type             = "ubuntu"
  }

  mount_point {
    volume = "/mnt/bindmounts/shared"
    path   = "/shared"
  }

}

resource "proxmox_virtual_environment_file" "ubuntu_container_template" {
  content_type = "vztmpl"
  datastore_id = "local"
  node_name    = "first-node"

  source_file {
    path = "http://download.proxmox.com/images/system/ubuntu-20.04-standard_20.04-1_amd64.tar.gz"
  }
}

resource "random_password" "ubuntu_container_password" {
  length           = 16
  override_special = "_%@"
  special          = true
}

resource "tls_private_key" "ubuntu_container_key" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

output "ubuntu_container_password" {
  value     = random_password.ubuntu_container_password.result
  sensitive = true
}

output "ubuntu_container_private_key" {
  value     = tls_private_key.ubuntu_container_key.private_key_pem
  sensitive = true
}

output "ubuntu_container_public_key" {
  value = tls_private_key.ubuntu_container_key.public_key_openssh
}