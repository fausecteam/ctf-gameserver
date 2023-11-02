resource "aws_vpc" "gamezone-vpc" {

  cidr_block         = var.gamezone-vpc-cidr
  enable_dns_hostnames = "true"
  enable_dns_support = "true"

  tags = {
    Name = "gamezone-vpc"
    Provisioner = "Terraform"
  }
}

#SUBNETS

resource "aws_subnet" "openvpn-team-subnet" {
  vpc_id                  = aws_vpc.gamezone-vpc.id
  cidr_block              = var.openvpn-team-subnet-cidr

  tags = {
    Name = "openvpn-team-subnet"
    Provisioner = "Terraform"
  }
}


resource "aws_subnet" "gameserver-subnet" {
  vpc_id                  = aws_vpc.gamezone-vpc.id
  cidr_block              = var.gameserver-subnet-cidr

  tags = {
    Name = "gameserver-subnet"
    Provisioner = "Terraform"
  }
}

resource "aws_subnet" "gamezone-nat-subnet" {
  vpc_id                  = aws_vpc.gamezone-vpc.id
  cidr_block              = var.gamezone-nat-subnet-cidr

  tags = {
    Name = "gamezone-nat-subnet"
    Provisioner = "Terraform"
  }
}

#GATEWAYS

resource "aws_internet_gateway" "gamezone-igw" {
	vpc_id = aws_vpc.gamezone-vpc.id

	tags = {
    	Name = "gamezone-igw"
      Provisioner = "Terraform"
	}
}

resource "aws_nat_gateway" "gamezone-ngw" {
  connectivity_type = "private"
  subnet_id         = aws_subnet.gamezone-nat-subnet.id

  tags = {
    Name = "gamezone-ngw"
    Provisioner = "Terraform"
  }
}

#ROUTE TABLES

#Gamezone teams and Gameserver rt

resource "aws_route_table" "gamezone-main-rt" {

	vpc_id = aws_vpc.gamezone-vpc.id

  route {
    	cidr_block = var.services-vpc-cidr
    	nat_gateway_id = aws_nat_gateway.gamezone-ngw.id
	}

	route {
    	cidr_block = var.internet-cidr
    	gateway_id = aws_internet_gateway.gamezone-igw.id
	}

  tags = {
    Name = "gamezone-main-rt"
  }
}

resource "aws_route_table_association" "gamezone-team-rt-assoc" {

  count = var.team_count

	subnet_id = aws_subnet.openvpn-team-subnet.id
	route_table_id = aws_route_table.gamezone-main-rt.id

}

resource "aws_route_table_association" "gamezone-gameserver-rt-assoc" {

  count = var.team_count

	subnet_id = aws_subnet.gameserver-subnet.id
	route_table_id = aws_route_table.gamezone-main-rt.id

}

#Gamezone nat rt

resource "aws_route_table" "gamezone-nat-rt" {

	vpc_id = aws_vpc.gamezone-vpc.id

  route {
    	cidr_block = var.services-vpc-cidr
    	transit_gateway_id = aws_ec2_transit_gateway.gamezone-services-tgw.id
	}

	# route {
  #   	cidr_block = var.internet-cidr
  #   	gateway_id = aws_internet_gateway.gamezone-igw.id
	# }

  tags = {
    Name = "gamezone-nat-rt"
  }
}

resource "aws_route_table_association" "gamezone-nat-rt-assoc" {

	subnet_id = aws_subnet.gamezone-nat-subnet.id
	route_table_id = aws_route_table.gamezone-nat-rt.id

}

#OpenVpn instance interfaces

resource "aws_network_interface" "openvpn-priv-interface" {

  subnet_id   = aws_subnet.openvpn-team-subnet.id
  security_groups = [
    aws_security_group.gamezone-allow-openvpn.id,
    aws_security_group.gamezone-allow-ssh.id,
  ]

  tags = {
    Name = "openvpn-priv-interface"
  }
}

#Gameserver instance interfaces

resource "aws_network_interface" "gameserver-priv-interface" {

  subnet_id   = aws_subnet.gameserver-subnet.id
  private_ips = [var.gameserver-priv-ip]
  security_groups = [
    aws_security_group.gamezone-allow-ssh.id,
    aws_security_group.gamezone-allow-web.id
  ]

  tags = {
    Name = "gameserver-pri-interface"
  }
}

#Gameserver openvpn instance interfaces

resource "aws_network_interface" "gameserver-openvpn-priv-interface" {

  subnet_id   = aws_subnet.gameserver-subnet.id
  security_groups = [
    aws_security_group.gamezone-allow-ssh.id,
    aws_security_group.gamezone-allow-openvpn.id
  ]

  tags = {
    Name = "gameserver-openvpn-priv-interface"
  }
}