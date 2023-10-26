resource "aws_security_group" "openvpn-allow-ssh" {
  name        = "allow-ssh"
  description = "Allow ssh inbound traffic"

  vpc_id      = aws_vpc.openvpn-vpc.id

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

resource "aws_security_group" "openvpn-allow-openvpn" {
  name        = "allow-openvpn"
  description = "Allow opennpn inbound traffic"

  vpc_id      = aws_vpc.openvpn-vpc.id

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

resource "aws_security_group" "team-allow-ssh" {
  name        = "team-allow-ssh"
  description = "Allow ssh inbound traffic"

  count = var.team_count

  vpc_id      = aws_vpc.team-vpc[count.index].id

  ingress {
    description      = "SSH"
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
    Name = "team-allow-ssh"
  }
}