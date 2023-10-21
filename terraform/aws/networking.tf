resource "aws_vpc" "team-vpc" {

  count = var.team_count

  cidr_block         = "10.0.${count.index}.0/24"
  enable_dns_hostnames = "true"
  enable_dns_support = "true"

  tags = {
    Name = "team${count.index}-vpc"
    Provisioner = "Terraform"
  }
}

resource "aws_subnet" "team-subnet" {

  count = var.team_count

  vpc_id                  = aws_vpc.team-vpc[count.index].id
  cidr_block              = "10.0.${count.index}.0/24"

  tags = {
    Name = "team${count.index}-subnet"
    Provisioner = "Terraform"
  }
}

resource "aws_internet_gateway" "team-gateway" {

  count = var.team_count

	vpc_id = aws_vpc.team-vpc[count.index].id

	tags = {
    	name = "team${count.index}gateway"
      Provisioner = "Terraform"
	}
}

resource "aws_route_table" "team-routetable" {

  count = var.team_count

	vpc_id = aws_vpc.team-vpc[count.index].id

	route {
    	cidr_block = "0.0.0.0/0"
    	gateway_id = aws_internet_gateway.team-gateway[count.index].id
	}
}

resource "aws_route_table_association" "asoc_public" {

  count = var.team_count

	subnet_id = aws_subnet.team-subnet[count.index].id
	route_table_id = aws_route_table.team-routetable[count.index].id
 
}

#OpenVpn instance interfaces

resource "aws_network_interface" "openvpn-priv-interface" {

  count = var.team_count

  subnet_id   = aws_subnet.team-subnet[count.index].id
  private_ips = ["10.0.${count.index}.100"]
  security_groups = [
    aws_security_group.allow-openvpn[count.index].id,
    aws_security_group.allow-ssh[count.index].id,
  ]

  tags = {
    Name = "openvpn-private-network-interface"
  }
}

#Service instance interfaces

resource "aws_network_interface" "service1-priv-interface" {

  count = var.team_count

  subnet_id   = aws_subnet.team-subnet[count.index].id
  private_ips = ["10.0.${count.index}.101"]
  security_groups = [aws_security_group.allow-ssh[count.index].id]


  tags = {
    Name = "service1-private-interface"
  }
}