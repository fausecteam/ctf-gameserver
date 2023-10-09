*using https://austinsnerdythings.com/2021/09/01/how-to-deploy-vms-in-proxmox-with-terraform/ as reference

Create teams enviroments in Proxmox using Terraform
===================================================

#1 - Install terraform
----------------------

```console
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=$(dpkg --print-architecture)] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt update
sudo apt install terraform

```

#2 - Create proxmox user with Api Token
---------------------------------------



#3 - Terraform initialization
-----------------------------

Repo terraform is not inizialized, so this is the first thing:

```console
terraform init
```

Now you we can make changes in files and can terraform plan, apply or destroy as we need.




