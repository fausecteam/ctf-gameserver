resource "aws_security_group" "allow-ssh" {
  name        = "allow-ssh"
  description = "Allow ssh inbound traffic"

  count = var.team_count

  vpc_id      = aws_vpc.team-vpc[count.index].id

  ingress {
    description      = "SSH from VPC"
    from_port        = 22
    to_port          = 22
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
  }

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
  }

  tags = {
    Name = "allow-ssh"
  }
}

resource "aws_security_group" "allow-openvpn" {
  name        = "allow-openvpn"
  description = "Allow opennpn inbound traffic"

  count = var.team_count

  vpc_id      = aws_vpc.team-vpc[count.index].id

  ingress {
    from_port   = 1194
    to_port     = 1194
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = -1
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "allow-openvpn"
  }
}