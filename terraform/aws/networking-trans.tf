#TRANSIT GATEAWAYS BEETWEEN TEAM and NAT VPCs"

resource "aws_ec2_transit_gateway" "gamezone-services-tgw" {

  default_route_table_association = "disable"
  default_route_table_propagation = "disable"

  description = "transit gateway from Gamezone-NAT to Team Services"

  tags               = {
    Name             = "gamezone-services-tgw"
  }
}

resource "aws_ec2_transit_gateway_vpc_attachment" "tgw-att-team-services" {
  depends_on = [ aws_ec2_transit_gateway.gamezone-services-tgw ]

  subnet_ids         = [aws_subnet.team-services-subnet[0].id]
  transit_gateway_id = aws_ec2_transit_gateway.gamezone-services-tgw.id
  vpc_id             = aws_vpc.team-services-vpc.id
  transit_gateway_default_route_table_association = false
  transit_gateway_default_route_table_propagation = false

  tags               = {
    Name             = "tgw-att-team-services"
  }
}

resource "aws_ec2_transit_gateway_vpc_attachment" "tgw-att-gamezone" {

  subnet_ids         = [aws_subnet.gamezone-nat-subnet.id]
  transit_gateway_id = aws_ec2_transit_gateway.gamezone-services-tgw.id
  vpc_id             = aws_vpc.gamezone-vpc.id
  transit_gateway_default_route_table_association = false
  transit_gateway_default_route_table_propagation = false
  tags               = {
    Name             = "tgw-att-services"
  }
  depends_on = [aws_ec2_transit_gateway.gamezone-services-tgw]
}

#Transit gateway routing

resource "aws_ec2_transit_gateway_route_table" "tgw-rt" {

  transit_gateway_id = aws_ec2_transit_gateway.gamezone-services-tgw.id
  tags               = {
    Name             = "tgw-rt"
  }
}

resource "aws_ec2_transit_gateway_route_table_association" "tgw-rt-team-services-assoc" {

  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.tgw-att-team-services.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.tgw-rt.id
}

resource "aws_ec2_transit_gateway_route_table_association" "tgw-rt-gamezone-assoc" {

  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.tgw-att-gamezone.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.tgw-rt.id
}

resource "aws_ec2_transit_gateway_route" "tgw-in-route-to-team-services" {
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.tgw-rt.id
  destination_cidr_block = var.internet-cidr
  transit_gateway_attachment_id = aws_ec2_transit_gateway_vpc_attachment.tgw-att-team-services.id
}

resource "aws_ec2_transit_gateway_route" "tgw-in-route-to-gamezone" {
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.tgw-rt.id
  destination_cidr_block = var.gamezone-nat-subnet-cidr
  transit_gateway_attachment_id = aws_ec2_transit_gateway_vpc_attachment.tgw-att-gamezone.id  
}