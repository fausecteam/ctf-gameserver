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

variable "aws-team-keys-folder"{
    description = "public key location base for all team"
    default = "output/team"  #usually with count.index ex: output/team1
}

variable "aws-opnevpn-private-key-name" {
    default = "openvpnkey"
}

variable "aws-openvpn-public-key-name" {
    default = "openvpnkey.pub"
}

variable "aws-ssh-private-key-name" {
    default = "sshkey"
}

variable "aws-ssh-public-key-name" {
    default     = "sshkey.pub"
}

variable "openvpn-instance-username" {
    description = "openvpn instace username"
    default = "ec2-user"
}

variable "service-instance-username" {
    type        = list
    description = "private key location for each team"
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
