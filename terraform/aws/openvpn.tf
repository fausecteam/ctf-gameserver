data "aws_ami" "amazon_linux_2" {
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

resource "aws_instance" "openvpn-team" {
  depends_on = [aws_network_interface.openvpn-priv-interface]

  ami                         = data.aws_ami.amazon_linux_2.id
#  associate_public_ip_address = true
  instance_type               = var.aws-instance-type

  count = var.team_count

  key_name                    = aws_key_pair.team-key[count.index].key_name

  network_interface {
    network_interface_id = aws_network_interface.openvpn-priv-interface[count.index].id
    device_index         = 0
  }

  root_block_device {
    volume_type           = "gp2"
    volume_size           = var.instance_root_block_device_volume_size
    delete_on_termination = true
  }

  tags = {
    Name        = "openvpn-team${count.index}"
  }
}

resource "aws_eip" "openvpn-eip" {
  count = var.team_count

  instance = aws_instance.openvpn-team[count.index].id
  vpc      = true
}

resource "null_resource" "openvpn-bootstrap" {
  count = var.team_count

  connection {
    type        = "ssh"
    host        = aws_eip.openvpn-eip[count.index].public_ip
    user        = var.openvpn-username
    port        = "22"
    private_key = file(var.aws-team-private-key[count.index])
    agent       = false
  }

  provisioner "remote-exec" {
    inline = [
      "sudo yum update -y",
      "curl -O ${var.openvpn-install-script-location}",
      "chmod +x openvpn-install.sh",
#      "sed -i -e 's/10.8.0/10.0.${count.index}/g' openvpn-install.sh",
      <<EOT
      sudo AUTO_INSTALL=y \
           APPROVE_IP=${aws_eip.openvpn-eip[count.index].public_ip} \
           ENDPOINT=${aws_eip.openvpn-eip[count.index].public_dns} \
           ./openvpn-install.sh
      EOT
      ,
    ]
  }
}

resource "null_resource" "openvpn-update-users-script" {
  depends_on = [null_resource.openvpn-bootstrap]

  count = var.team_count

  triggers = {
    ovpn_users = join(" ", var.ovpn-users)
  }

  connection {
    type        = "ssh"
    host        = aws_eip.openvpn-eip[count.index].public_ip
    user        = var.openvpn-username
    port        = "22"
    private_key = file(var.aws-team-private-key[count.index])
    agent       = false
  }

  provisioner "file" {
    source      = "scripts/update_users.sh"
    destination = "/home/${var.openvpn-username}/update_users.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /home/${var.openvpn-username}/update_users.sh",
      "sudo /home/${var.openvpn-username}/update_users.sh ${join(" ", var.ovpn-users)}"
    ]
  }
}

resource "null_resource" "openvpn-download-configurations" {
  depends_on = [null_resource.openvpn-update-users-script]

  count = var.team_count

  triggers = {
    ovpn_users = join(" ", var.ovpn-users)
  }

  provisioner "local-exec" {
    command = <<EOT
    mkdir -p ${var.ovpn-config-directory};
    scp -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -i ${var.aws-team-private-key[count.index]} ${var.openvpn-username}@${aws_eip.openvpn-eip[count.index].public_ip}:/home/${var.openvpn-username}/*.ovpn ${var.ovpn-config-directory}/

EOT

  }
}

