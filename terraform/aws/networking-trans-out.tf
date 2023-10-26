#TRANSIT GATEAWAYS BEETWEEN TEAM and NAT VPCs"

resource "aws_ec2_transit_gateway" "team-transit-out-gateway" {

  count = var.team_count

  default_route_table_association = "disable"
  default_route_table_propagation = "disable"

  description = "transit gateway from Team to NAT"

  tags               = {
    Name             = "tgw-out${count.index}"
  }
}

resource "aws_ec2_transit_gateway_vpc_attachment" "tgw-out-att-team" {

  count = var.team_count

  subnet_ids         = [aws_subnet.team-subnet[count.index].id]
  transit_gateway_id = aws_ec2_transit_gateway.team-transit-out-gateway[count.index].id
  vpc_id             = aws_vpc.team-vpc[count.index].id
  transit_gateway_default_route_table_association = false
  transit_gateway_default_route_table_propagation = false
  tags               = {
    Name             = "tgw-out-att-team${count.index}"
  }
  depends_on = [aws_ec2_transit_gateway.team-transit-out-gateway]
}

resource "aws_ec2_transit_gateway_vpc_attachment" "tgw-out-att-nat" {

  count = var.team_count

  subnet_ids         = [aws_subnet.nat-out-subnet[count.index].id]
  transit_gateway_id = aws_ec2_transit_gateway.team-transit-out-gateway[count.index].id
  vpc_id             = aws_vpc.nat-vpc.id
  transit_gateway_default_route_table_association = false
  transit_gateway_default_route_table_propagation = false
  tags               = {
    Name             = "tgw-out-att-nat${count.index}"
  }
  depends_on = [aws_ec2_transit_gateway.team-transit-out-gateway]
}

#Transit gateway routing

resource "aws_ec2_transit_gateway_route_table" "tgw-out-rt" {

  count = var.team_count

  transit_gateway_id = aws_ec2_transit_gateway.team-transit-out-gateway[count.index].id
  tags               = {
    Name             = "tgw-out-rt${count.index}"
  }
  depends_on = [aws_ec2_transit_gateway.team-transit-out-gateway]
}

resource "aws_ec2_transit_gateway_route_table_association" "tgw-out-rt-team-assoc" {

  count = var.team_count

  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.tgw-out-att-team[count.index].id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.tgw-out-rt[count.index].id
}

resource "aws_ec2_transit_gateway_route_table_association" "tgw-out-rt-nat-assoc" {

  count = var.team_count

  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.tgw-out-att-nat[count.index].id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.tgw-out-rt[count.index].id
}

resource "aws_ec2_transit_gateway_route" "tgw-out-route-to-team" {
  count = var.team_count

  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.tgw-out-rt[count.index].id
  destination_cidr_block = "10.0.${count.index}.0/24"
  transit_gateway_attachment_id = aws_ec2_transit_gateway_vpc_attachment.tgw-out-att-team[count.index].id
}

resource "aws_ec2_transit_gateway_route" "tgw-out-route-to-nat-out" {
  count = var.team_count

  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.tgw-out-rt[count.index].id
  destination_cidr_block = "10.0.0.0/16"  
  transit_gateway_attachment_id = aws_ec2_transit_gateway_vpc_attachment.tgw-out-att-nat[count.index].id  
}