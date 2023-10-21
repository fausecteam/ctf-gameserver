resource "aws_key_pair" "team-key"{

    count = var.team_count

    key_name = "team${count.index}-key"
    public_key = file(var.aws-team-public-key[count.index])
}