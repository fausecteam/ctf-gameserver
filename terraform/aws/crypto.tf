resource "aws_key_pair" "team-ssh-key"{

    count = var.team_count

    key_name = "team-ssh-key${count.index}"
    public_key = file("${var.aws-team-keys-folder}${count.index}/${var.aws-ssh-public-key-name}")
}