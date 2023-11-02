#Output folders creation

resource "null_resource" "output-main-folder" {

  provisioner "local-exec" {
    command = "mkdir output 2>&1"
  }
}

resource "null_resource" "output-team-folders" {
  depends_on = [null_resource.output-main-folder]

  count = var.team_count

  provisioner "local-exec" {
    command = "mkdir output/team${count.index}"
  }
}

#Keys

resource "tls_private_key" "gameserver-openvpn-instance-tls-key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# resource "tls_private_key" "gameserver-openvpn-tls-key" {
#   algorithm = "RSA"
#   rsa_bits  = 4096
# }

resource "tls_private_key" "gameserver-tls-key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "tls_private_key" "team-openvpn-instance-tls-key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# resource "tls_private_key" "team-openvpn-tls-key" {
#   algorithm = "RSA"
#   rsa_bits  = 4096
# }

resource "tls_private_key" "team-tls-key" {
  count = var.team_count

  algorithm = "RSA"
  rsa_bits  = 4096
}

#AWS key pairs

resource "aws_key_pair" "gameserver-openvpn-instance-ssh-key"{
    key_name = "gameserver-instance-openvpn-ssh-key"
    public_key = tls_private_key.gameserver-openvpn-instance-tls-key.public_key_openssh
}

# resource "aws_key_pair" "gameserver-openvpn-ssh-key"{
#     key_name = "openvpn-ssh-key"
#     public_key = tls_private_key.gameserver-openvpn-tls-key.public_key_openssh
# }

resource "aws_key_pair" "gameserver-ssh-key"{
    key_name = "gameserver-ssh-key"
    public_key = tls_private_key.gameserver-tls-key.public_key_openssh
}

resource "aws_key_pair" "team-openvpn-instance-ssh-key"{
    key_name = "openvpn-instance-ssh-key"
    public_key = tls_private_key.team-openvpn-instance-tls-key.public_key_openssh
}

# resource "aws_key_pair" "team-openvpn-ssh-key"{
#     key_name = "team-openvpn-ssh-key"
#     public_key = tls_private_key.team-openvpn-tls-key.public_key_openssh
# }

resource "aws_key_pair" "team-ssh-key"{
    count = var.team_count

    key_name = "team-ssh-key${count.index}"
    public_key = tls_private_key.team-tls-key[count.index].public_key_openssh
}

#Save private key to file

resource "local_file" "master-openvpn-instance-private-key-file" {
    depends_on = [null_resource.output-team-folders]

    file_permission = "600"
    content  = tls_private_key.gameserver-openvpn-instance-tls-key.private_key_openssh
    filename = "output/master-openvpn-instance-sshkey"
}

resource "local_file" "master-private-key-file" {
    depends_on = [null_resource.output-team-folders]

    file_permission = "600"
    content  = tls_private_key.gameserver-tls-key.private_key_openssh
    filename = "output/master-sshkey"
}

resource "local_file" "team-openvpn-instance-private-key-file" {
    depends_on = [null_resource.output-team-folders]

    file_permission = "600"
    content  = tls_private_key.team-openvpn-instance-tls-key.private_key_openssh
    filename = "output/openvpn-instance-sshkey"
}

resource "local_file" "team-private-key-file" {
    depends_on = [null_resource.output-team-folders]

    count = var.team_count
    
    file_permission = "600"
    content  = tls_private_key.team-tls-key[count.index].private_key_openssh
    filename = "output/team${count.index}/team${count.index}-sshkey"
}

# resource "null_resource" "change-key-permisions" {
#   depends_on = [
#     local_file.master-openvpn-instance-private-key-file,
#     local_file.master-private-key-file,
#     local_file.team-openvpn-instance-private-key-file,
#     local_file.team-private-key-file
#   ]

#   provisioner "local-exec" {
#     command = "chmod 600 output/*key && chmod 600 output/team*/*key"
#   }
# }