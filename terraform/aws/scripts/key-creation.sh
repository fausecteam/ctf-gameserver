#!/bin/bash

read -p "How many teams are there? " team_count

for (( c=0; c<$team_count; c++ ))
do
    mkdir "output/team$c"
    ssh-keygen -b 2048 -t rsa -f output/team$c/sshkey -q -N ""
    ssh-keygen -b 2048 -t rsa -f output/team$c/openvpnkey -q -N ""
done