resource "aws_vpc" "openvpn-vpc" {

  cidr_block         = "10.255.0.0/16"
  enable_dns_hostnames = "true"
  enable_dns_support = "true"

  tags = {
    Name = "openvpn-vpc"
    Provisioner = "Terraform"
  }
}

#SUBNETS

resource "aws_subnet" "openvpn-team-subnet" {

  count = var.team_count

  vpc_id                  = aws_vpc.openvpn-vpc.id
  cidr_block              = "10.255.${count.index}.0/24"

  tags = {
    Name = "openvpn-team-subnet${count.index}"
    Provisioner = "Terraform"
  }
}

resource "aws_subnet" "openvpn-nat-subnet" {
  vpc_id                  = aws_vpc.openvpn-vpc.id
  cidr_block              = "10.255.255.0/24"

  tags = {
    Name = "opepnvpn-nat-subnet"
    Provisioner = "Terraform"
  }
}

#GATEWAYS

resource "aws_internet_gateway" "openvpn-igw" {
	vpc_id = aws_vpc.openvpn-vpc.id

	tags = {
    	Name = "openvpn-igw"
      Provisioner = "Terraform"
	}
}

resource "aws_nat_gateway" "openvpn-ngw" {
  connectivity_type = "private"
  subnet_id         = aws_subnet.openvpn-nat-subnet.id

  tags = {
    Name = "openvpn-ngw"
    Provisioner = "Terraform"
  }
}

#ROUTE TABLES

#Openvpn teams rt

resource "aws_route_table" "openvpn-team-rt" {

	vpc_id = aws_vpc.openvpn-vpc.id

  route {
    	cidr_block = "10.0.0.0/16"
    	nat_gateway_id = aws_nat_gateway.openvpn-ngw.id
	}

	route {
    	cidr_block = "0.0.0.0/0"
    	gateway_id = aws_internet_gateway.openvpn-igw.id
	}

  tags = {
    Name = "openvpn-team-rt"
  }
}

resource "aws_route_table_association" "openvpn-team-rt-assoc" {

  count = var.team_count

	subnet_id = aws_subnet.openvpn-team-subnet[count.index].id
	route_table_id = aws_route_table.openvpn-team-rt.id

}

#Openvpn nat rt

resource "aws_route_table" "openvpn-nat-rt" {

	vpc_id = aws_vpc.openvpn-vpc.id

  route {
    	cidr_block = "10.0.0.0/16"
    	transit_gateway_id = aws_ec2_transit_gateway.openvpn-team-tgw.id
	}

	route {
    	cidr_block = "0.0.0.0/0"
    	gateway_id = aws_internet_gateway.openvpn-igw.id
	}

  tags = {
    Name = "openvpn-nat-rt"
  }
}

resource "aws_route_table_association" "openvpn-nat-rt-assoc" {

	subnet_id = aws_subnet.openvpn-nat-subnet.id
	route_table_id = aws_route_table.openvpn-nat-rt.id

}

#OpenVpn instance interfaces

resource "aws_network_interface" "openvpn-priv-interface" {

  count = var.team_count

  subnet_id   = aws_subnet.openvpn-team-subnet[count.index].id
  private_ips = ["10.255.${count.index}.100"]
  security_groups = [
    aws_security_group.openvpn-allow-openvpn.id,
    aws_security_group.openvpn-allow-ssh.id,
  ]

  tags = {
    Name = "openvpn-private-interface${count.index}"
  }
}