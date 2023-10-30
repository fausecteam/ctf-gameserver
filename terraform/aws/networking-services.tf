resource "aws_vpc" "team-services-vpc" {

  cidr_block         = var.services-vpc-cidr
  enable_dns_hostnames = "true"
  enable_dns_support = "true"

  tags = {
    Name = "team-services-vpc"
    Provisioner = "Terraform"
  }
}

resource "aws_subnet" "team-services-subnet" {

  count = var.team_count

  vpc_id                  = aws_vpc.team-services-vpc.id
  cidr_block              = "${var.team-services-subnet-cidr-init}.${count.index}.0/24"

  tags = {
    Name = "team-services-subnet${count.index}"
    Provisioner = "Terraform"
  }
}

resource "aws_route_table" "team-services-rt" {
  depends_on = [ aws_ec2_transit_gateway_vpc_attachment.tgw-att-team-services ]

	vpc_id = aws_vpc.team-services-vpc.id

  route {
    	cidr_block = var.gamezone-nat-subnet-cidr
    	transit_gateway_id = aws_ec2_transit_gateway.gamezone-services-tgw.id
	}

	route {
    	cidr_block = var.internet-cidr
    	nat_gateway_id = aws_nat_gateway.service-egress-ngw.id
	}

  tags = {
    Name = "team-services-rt"
  }
}

resource "aws_route_table_association" "team-services-rt-asoc" {

  count = var.team_count

	subnet_id = aws_subnet.team-services-subnet[count.index].id
	route_table_id = aws_route_table.team-services-rt.id
 
}

#Service instance interfaces

resource "aws_network_interface" "service1-priv-interface" {

  count = var.team_count

  subnet_id   = aws_subnet.team-services-subnet[count.index].id
  private_ips = ["${var.team-services-subnet-cidr-init}.${count.index}.101"]
  security_groups = [aws_security_group.team-services-allow-ssh.id]

  tags = {
    Name = "service1-private-interface${count.index}"
  }
}