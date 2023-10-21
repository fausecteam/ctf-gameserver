variable "aws-region" { 
    default = "us-east-1" 
}

variable "aws_access_key_id" {  
}

variable "aws_secret_access_key" {
}

variable "aws_session_token" {
}


variable "aws-instance-type" { 
    default = "t2.micro" 
}

variable "instance_root_block_device_volume_size" {
  description = "The size of the root block device volume of the EC2 instance in GiB"
  default     = 8
}

variable "team_count"{
    description = "how many teams will play"
}

variable "aws-team-public-key"{
    type = list
    description = "public key location for each team"
}

variable "aws-team-private-key" {
    type        = list
    description = "private key location for each team"
}

variable "openvpn-username" {
    description = "openvpn instace username"
    default = "ec2-user"
}

variable "ovpn-users" {
    type        = list(string)
    description = "vpn access users"
}

variable "ovpn-config-directory" {
    default = "secrets"
}

variable "openvpn-install-script-location" {
    default = "https://raw.githubusercontent.com/dumrauf/openvpn-install/master/openvpn-install.sh"
}
