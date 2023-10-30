resource "aws_security_group" "gamezone-allow-ssh" {
  name        = "allow-ssh"
  description = "Allow ssh inbound traffic"

  vpc_id      = aws_vpc.gamezone-vpc.id

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
    Name = "gamezone-allow-ssh"
  }
}

resource "aws_security_group" "gamezone-allow-openvpn" {
  name        = "allow-openvpn"
  description = "Allow opennpn inbound traffic"

  vpc_id      = aws_vpc.gamezone-vpc.id

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
    Name = "gamezon-allow-openvpn"
  }
}

resource "aws_security_group" "team-services-allow-ssh" {
  name        = "team-allow-ssh"
  description = "Allow ssh inbound traffic"

  vpc_id      = aws_vpc.team-services-vpc.id

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
    Name = "team-services-allow-ssh"
  }
}