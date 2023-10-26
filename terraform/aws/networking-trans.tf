#TRANSIT GATEAWAYS BEETWEEN TEAM and NAT VPCs"

resource "aws_ec2_transit_gateway" "openvpn-team-tgw" {

  default_route_table_association = "disable"
  default_route_table_propagation = "disable"

  description = "transit gateway from NAT to Team"

  tags               = {
    Name             = "openvpn-tgw"
  }
}

resource "aws_ec2_transit_gateway_vpc_attachment" "tgw-att-team" {

  count = var.team_count

  subnet_ids         = [aws_subnet.team-subnet[count.index].id]
  transit_gateway_id = aws_ec2_transit_gateway.openvpn-team-tgw.id
  vpc_id             = aws_vpc.team-vpc[count.index].id
  transit_gateway_default_route_table_association = false
  transit_gateway_default_route_table_propagation = false
  tags               = {
    Name             = "tgw-att-team${count.index}"
  }
  depends_on = [aws_ec2_transit_gateway.openvpn-team-tgw]
}

resource "aws_ec2_transit_gateway_vpc_attachment" "tgw-att-openvpn" {

  subnet_ids         = [aws_subnet.openvpn-nat-subnet.id]
  transit_gateway_id = aws_ec2_transit_gateway.openvpn-team-tgw.id
  vpc_id             = aws_vpc.openvpn-vpc.id
  transit_gateway_default_route_table_association = false
  transit_gateway_default_route_table_propagation = false
  tags               = {
    Name             = "tgw-att-openvpn"
  }
  depends_on = [aws_ec2_transit_gateway.openvpn-team-tgw]
}

#Transit gateway routing

resource "aws_ec2_transit_gateway_route_table" "tgw-rt" {

  transit_gateway_id = aws_ec2_transit_gateway.openvpn-team-tgw.id
  tags               = {
    Name             = "tgw-rt"
  }
  depends_on = [aws_ec2_transit_gateway.openvpn-team-tgw]
}

resource "aws_ec2_transit_gateway_route_table_association" "tgw-rt-team-assoc" {

  count = var.team_count

  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.tgw-att-team[count.index].id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.tgw-rt.id
}

resource "aws_ec2_transit_gateway_route_table_association" "tgw-rt-openvpn-assoc" {

  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.tgw-att-openvpn.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.tgw-rt.id
}

resource "aws_ec2_transit_gateway_route" "tgw-in-route-to-team" {
  count = var.team_count

  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.tgw-rt.id
  destination_cidr_block = "10.0.${count.index}.0/24"
  transit_gateway_attachment_id = aws_ec2_transit_gateway_vpc_attachment.tgw-att-team[count.index].id
}

resource "aws_ec2_transit_gateway_route" "tgw-in-route-to-openvpn" {
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.tgw-rt.id
  destination_cidr_block = "10.255.255.0/24"
  transit_gateway_attachment_id = aws_ec2_transit_gateway_vpc_attachment.tgw-att-openvpn.id  
}