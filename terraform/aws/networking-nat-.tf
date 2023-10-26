##VPC for NAT between TEAMs

resource "aws_vpc" "nat-vpc" {
  cidr_block         = "10.1.0.0/16"
  enable_dns_hostnames = "true"
  enable_dns_support = "true"

  tags = {
    Name = "nat-vpc"
    Provisioner = "Terraform"
  }
}

resource "aws_subnet" "nat-out-subnet" {
  count = var.team_count

  vpc_id                  = aws_vpc.nat-vpc.id
  cidr_block              = "10.1.${count.index}.0/24"

  tags = {
    Name = "nat-out-subnet${count.index}"
    Provisioner = "Terraform"
  }
}

resource "aws_subnet" "nat-in-subnet" {
  count = var.team_count

  vpc_id                  = aws_vpc.nat-vpc.id
  cidr_block              = "10.1.${128+count.index}.0/24"

  tags = {
    Name = "nat-in-subnet${count.index}"
    Provisioner = "Terraform"
  }
}


resource "aws_nat_gateway" "nat-gateway" {
  count = var.team_count

  connectivity_type = "private"
  subnet_id         = aws_subnet.nat-in-subnet[count.index].id
  private_ip        = "10.1.${128+count.index}.254"

  tags = {
    Name = "nat-gw${count.index}"
    Provisioner = "Terraform"
  }
}

#################################
# Nat VPC routing (1) NAT-out subnet

resource "aws_route_table" "nat-out-rt" {
  count = var.team_count

	vpc_id = aws_vpc.nat-vpc.id

  tags = {
    Name = "nat-out-rt${count.index}"
  }
}

resource "aws_route" "nat-out-team-route" {
  count = var.team_count

  route_table_id         = aws_route_table.nat-out-rt[count.index].id
  destination_cidr_block = "10.0.${count.index}.0/24"
  transit_gateway_id = aws_ec2_transit_gateway.team-transit-out-gateway[count.index].id 

  depends_on = [aws_ec2_transit_gateway.team-transit-out-gateway]
}

resource "aws_route" "nat-out-nat-in-route" {
  for_each = {for val in setproduct(range(0,var.team_count), range(0,var.team_count)):
                "${val[0]}-${val[1]}" => val if val[0] != val[1]}

  route_table_id         = aws_route_table.nat-out-rt[each.value[0]].id
  destination_cidr_block = "10.0.${each.value[1]}.0/24"
  nat_gateway_id = aws_nat_gateway.nat-gateway[each.value[1]].id
}

resource "aws_route_table_association" "asoc_nat_out" {
  count = var.team_count

	subnet_id = aws_subnet.nat-out-subnet[count.index].id
	route_table_id = aws_route_table.nat-out-rt[count.index].id
}


#Nat VPC routing (1) NAT-in subnet

resource "aws_route_table" "nat-in-rt" {
  count = var.team_count

	vpc_id = aws_vpc.nat-vpc.id

  tags = {
    Name = "nat-in-rt${count.index}"
  }
}

resource "aws_route" "nat-in-team-route" {
  count = var.team_count

  route_table_id         = aws_route_table.nat-in-rt[count.index].id
  destination_cidr_block = "10.0.${count.index}.0/24"
  transit_gateway_id = aws_ec2_transit_gateway.team-transit-in-gateway[count.index].id 

  depends_on = [aws_ec2_transit_gateway.team-transit-out-gateway]
}

resource "aws_route" "nat-in-nat-out-route" {
  for_each = {for val in setproduct(range(0,var.team_count), range(0,var.team_count)):
                "${val[0]}-${val[1]}" => val if val[0] != val[1]}

  route_table_id         = aws_route_table.nat-in-rt[each.value[0]].id
  destination_cidr_block = "10.0.${each.value[1]}.0/24"
  transit_gateway_id = aws_ec2_transit_gateway.team-transit-out-gateway[each.value[1]].id 
}

resource "aws_route_table_association" "asoc_nat_in" {
  count = var.team_count

	subnet_id = aws_subnet.nat-in-subnet[count.index].id
	route_table_id = aws_route_table.nat-in-rt[count.index].id
 
}