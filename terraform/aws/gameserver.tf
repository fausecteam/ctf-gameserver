resource "aws_instance" "gameserver" {
  ami                         = "ami-04cbc90abb08f0321"
  instance_type               = var.aws-instance-type

  key_name                    = aws_key_pair.gameserver-ssh-key.key_name

  network_interface {
    network_interface_id = aws_network_interface.gameserver-priv-interface.id
    device_index         = 0
  }

  root_block_device {
    volume_type           = "gp2"
    volume_size           = var.instance_root_block_device_volume_size
    delete_on_termination = true
  }

  tags = {
    Name        = "gameserver"
  }
}

resource "aws_eip" "gameserver-eip" {
  instance = aws_instance.gameserver.id
  vpc      = true
}
