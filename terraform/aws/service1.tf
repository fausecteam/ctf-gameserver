resource "aws_instance" "team-service1" {
  ami           = "ami-04cbc90abb08f0321"
  instance_type = var.aws-instance-type

  count = var.team_count

  key_name = aws_key_pair.team-ssh-key[count.index].key_name
  
  network_interface {
    network_interface_id = aws_network_interface.service1-priv-interface[count.index].id
    device_index         = 0
  }

  tags = {
   Name = "Team${count.index}-service1"
 }
}

# resource "aws_eip" "team-eip" {
#   count = var.team_count

#   instance = aws_instance.team-service1[count.index].id
#   vpc      = true
# }
