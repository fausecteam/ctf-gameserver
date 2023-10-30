resource "aws_subnet" "services-egress-nat-subnet" {

  vpc_id      = aws_vpc.team-services-vpc.id
  cidr_block  = var.services-egress-nat-subnet-cidr

  tags = {
    Name = "services-egress-nat-subnet"
    Provisioner = "Terraform"
  }
}


resource "aws_eip" "service-egress-eip" {
  vpc      = true
}

resource "aws_internet_gateway" "services-egress-igw" {
  vpc_id      = aws_vpc.team-services-vpc.id

	tags = {
    	Name = "services-egress-igw"
      Provisioner = "Terraform"
	}
}

resource "aws_nat_gateway" "service-egress-ngw" {
  allocation_id = aws_eip.service-egress-eip.id
  subnet_id     = aws_subnet.services-egress-nat-subnet.id

  tags = {
      Name = "service-egress-ngw"
      Provisioner = "Terraform"
  }
}

#Egress subnet routing

resource "aws_route_table" "services-egress-nat-rt" {
  depends_on = [ aws_ec2_transit_gateway_vpc_attachment.tgw-att-team-services ]

	vpc_id = aws_vpc.team-services-vpc.id

  route {
    	cidr_block = var.gamezone-vpc-cidr
    	transit_gateway_id = aws_ec2_transit_gateway.gamezone-services-tgw.id
	}

	route {
    	cidr_block = var.internet-cidr
    	gateway_id = aws_internet_gateway.services-egress-igw.id
	}

  tags = {
    Name = "services-egress-nat-rt"
  }
}

resource "aws_route_table_association" "services-egress-nat-rt-asoc" {

	subnet_id = aws_subnet.services-egress-nat-subnet.id
	route_table_id = aws_route_table.services-egress-nat-rt.id 
}
