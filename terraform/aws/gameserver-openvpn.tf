data "aws_ami" "gameserver-amazon_linux_2" {
  most_recent = true

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm*"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "block-device-mapping.volume-type"
    values = ["gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["amazon"]
}

resource "aws_instance" "gameserver-openvpn" {
  depends_on = [aws_network_interface.gameserver-openvpn-priv-interface]

  ami                         = data.aws_ami.gameserver-amazon_linux_2.id
  instance_type               = var.aws-instance-type

  key_name                    = aws_key_pair.gameserver-openvpn-instance-ssh-key.key_name

  network_interface {
    network_interface_id = aws_network_interface.gameserver-openvpn-priv-interface.id
    device_index         = 0
  }

  root_block_device {
    volume_type           = "gp2"
    volume_size           = var.instance_root_block_device_volume_size
    delete_on_termination = true
  }

  tags = {
    Name        = "gameserver-openvpn"
  }
}

resource "aws_eip" "gameserver-openvpn-eip" {
  instance = aws_instance.gameserver-openvpn.id
  vpc      = true
}

resource "null_resource" "gameserver-openvpn-bootstrap" {

  connection {
    type        = "ssh"
    host        = aws_eip.gameserver-openvpn-eip.public_ip
    user        = var.openvpn-instance-username
    port        = "22"
    private_key = tls_private_key.gameserver-openvpn-instance-tls-key.private_key_openssh
    agent       = false
  }

  provisioner "remote-exec" {
    inline = [
      "sudo yum update -y",
      "curl -O ${var.openvpn-install-script-location}",
      "chmod +x openvpn-install.sh",
      <<EOT
      sudo AUTO_INSTALL=y \
           APPROVE_IP=${aws_eip.gameserver-openvpn-eip.public_ip} \
           ENDPOINT=${aws_eip.gameserver-openvpn-eip.public_dns} \
           ./openvpn-install.sh
      EOT
      ,
    ]
  }
}

resource "null_resource" "gameserver-openvpn-update-users-script" {
  depends_on = [null_resource.gameserver-openvpn-bootstrap]

  triggers = {
    ovpn_users = join(" ", var.ovpn-users)
  }

  connection {
    type        = "ssh"
    host        = aws_eip.gameserver-openvpn-eip.public_ip
    user        = var.openvpn-instance-username
    port        = "22"
    private_key = tls_private_key.gameserver-openvpn-instance-tls-key.private_key_openssh
    agent       = false
  }

  provisioner "file" {
    source      = "scripts/update_users.sh"
    destination = "/home/${var.openvpn-instance-username}/update_users.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /home/${var.openvpn-instance-username}/update_users.sh",
      "sudo /home/${var.openvpn-instance-username}/update_users.sh ${join(" ", ["master"])}"
    ]
  }
}

resource "null_resource" "gameserver-openvpn-download-configurations" {
  depends_on = [null_resource.gameserver-openvpn-update-users-script,
                local_file.master-openvpn-instance-private-key-file]

  triggers = {
    ovpn_users = join(" ", var.ovpn-users)
  }

  provisioner "local-exec" {
    command = <<EOT
    scp -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -i ${var.aws-gameserver-openvpn-instance-private-key} ${var.openvpn-instance-username}@${aws_eip.gameserver-openvpn-eip.public_ip}:/home/${var.openvpn-instance-username}/*.ovpn output/
    EOT

  }
}

