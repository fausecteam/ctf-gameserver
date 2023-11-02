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
    type = number
    description = "how many teams will play"
}

#SSH key variables

# variable "aws-team-keys-folder"{
#     description = "public key location base for all team"
#     default = "output/team"  #usually with count.index ex: output/team1
# }

variable "aws-gameserver-openvpn-instance-private-key" {
    default = "output/master-openvpn-instance-sshkey"
}

# variable "aws-gameserver-public-key" {
#     default = "output/gameserver-sshkey.pub"
# }

variable "aws-opnevpn-instance-private-key" {
    default = "output/openvpn-instance-sshkey"
}

# variable "aws-openvpn-public-key" {
#     default = "openvpnkey.pub"
# }

# variable "aws-opnevpn-instance-private-key" {
#     default = "output/openvpnkey"
# }

# variable "aws-openvpn-instance-public-key" {
#     default = "output/openvpnkey.pub"
# }


# variable "aws-ssh-private-key-name" {
#     default = "sshkey"
# }

# variable "aws-ssh-public-key-name" {
#     default = "sshkey.pub"
# }

#Gameserver variables

variable "gameserver-instance-username" {
    description = "gameserver instance username"
    default     = "ubuntu"
}

#Services variables

variable "service-instance-username" {
    type        = list
    description = "service instance username"
}

#Openvpn variables

variable "openvpn-instance-username" {
    description = "openvpn instace username"
    default = "ec2-user"
}

variable "ovpn-users" {
    type        = list(string)
    description = "vpn access users"
}

variable "ovpn-config-directory" {
    default = "output/team"  #usually with count.index ex: output/team1
}

variable "openvpn-install-script-location" {
    default = "https://raw.githubusercontent.com/dumrauf/openvpn-install/master/openvpn-install.sh"
}

#VPC CIDRs

variable "services-vpc-cidr" {
    #first two block
    default = "10.0.0.0/16"
}

# variable "services-egress-vpc-cidr" {
#     #first two block
#     default = "10.128.0.0/16"
# }


variable "gamezone-vpc-cidr" {
    #first two block
    default = "10.255.0.0/16"
}

#Subnet CIDRs

variable "team-services-subnet-cidr-init" {
    #first two block
    default = "10.0"
}

# variable "services-egress-subnet-cidr" {
#     #first two block
#     default = "10.0.255.0/24"
# }

variable "services-egress-nat-subnet-cidr" {
    #first two block
    default = "10.0.255.0/24"
}

variable "openvpn-team-subnet-cidr" {
    default = "10.255.0.0/17"
}

variable "gameserver-subnet-cidr" {
    default = "10.255.254.0/24"
}

variable "gamezone-nat-subnet-cidr" {
    default = "10.255.255.0/24"
}

variable "internet-cidr" {
    default = "0.0.0.0/0"
}

#Instances private IPs

variable "gameserver-priv-ip" {
    default = "10.255.254.200"
}

