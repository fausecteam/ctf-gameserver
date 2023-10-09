#######
#One VLAN per Team

resource "proxmox_virtual_environment_network_linux_vlan" "vlanteam" {

  node_name = var.PROXMOX_NODE
  count   = var.TEAM_COUNT
  name    = "eno0.${count}"
  comment = "VLAN ${count}"
}

#######
#One bridge per Team

resource "proxmox_virtual_environment_network_linux_bridge" "vmbrteam" {
  # depends_on = [
  #  proxmox_virtual_environment_network_linux_vlan.vlan99
  # ]

  node_name = var.PROXMOX_NODE
  count   = var.TEAM_COUNT
  name    = "vmbrteam${count}"
  comment = "Bridge ${count}"

  # address = "99.99.99.99/16"

  # ports = [
  #   "ens18.99"
  # ]
}

