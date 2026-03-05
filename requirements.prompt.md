I want to create a web app in a docker container which resembles AWS EKS and can provision VMs/nodes but for on-premises datacenter:

* Some high level thoughts:

  * Each instance of the server act as a "manager" for a "datacenter". We assume all host machines managed by the server is in the same datacenter, user should configure a 2-letter datacenter name when starting the server.
  * Considering we have hosts under multiple NAT networks, an entire datacenter must reside under the same NAT network. But each NAT network can have multiple datacenters.
  * For simplicity, we just assign static IP addresses to provisioned VMs, and we can have a global config for user to specify IP ranges that each manager can allocate, and each manager will keep track of assigned IPs to avoid conflict
  * Each docker container should contain a software server acting as gateway to other NAT networks; I'm not sure which server to use, and whether it has auto mesh network discovery. Worst case, it can consume a config file, listing public IP of "managers" of all data centers, so that it can route traffic to hosts/VMs in other datacenters

* The web server should be able to manage a cluster of physical machines (in the same network) via SSH, where we can use to provision VMs

  * Each host is uniquely identified by its IP + port (default 22)
  * Each host acts like a "virtual rack" in the datacenter, and VMs act as individual machines, it should auto assign a customizable but unique "rack" name for each host, and use it to group provisioned VMs (by default, just 2-letter [a-z])
  * It should auto detect host's hardware info (num CPUs, RAM, disk), network info (gateway, subnetmask, dns, etc) and use it to set up bridged network connection for provisioned VMs
  * It should support all of Linux/Mac/Windows hosts

* As a foundation, the web server should be able to provision a set of VMs of various sizes on a given set of physical machines

  * VM name should be auto-assigned as <2-letter datacenter><virtual rack><2-digit number>
  * It should allow users to generate new or reuse existing ssh keys, and setup VMs with user selected key
  * Please consider leveraging existing softwares like multipass or something better, if required software is not available to provision VMs, show commands for user to install them
  * It should set up bridged network connection for the provisioned VMs
  * It should setup unique static IP address for each provisioned VM
  * If needed, it should configure the gateway to other NAT networks
  * It should be able to pull the status of each VM (which virtual rack, on/off/unknown, IP address, num CPU, RAM, disk, OS info)

* The web server should allow users to create a K8S cluster

  * User just need to specify the number of control plane nodes and worker nodes, and the server will automatically provision VMs for them
  * It should try to distribute the nodes across all available hosts, but show num of nodes on each host and allows user to customize if they need
  * It should show all the nodes, grouped by type and virtual rack.
  * User should be able to add new nodes or remove specific nodes
  * Since the server keeps track of the SSH keys of the VMs, it should be able to do the setups via SSH at least, but feel free to suggest better ways if any

Follow up design considerations and issues:

* Networking:

  * For "Cloud-Init Network Configuration", it seems we don't have config to route to WireGuard gateway?
  * What if we have 2 datacenters in the same NAT LAN? can we just let one WireGuard instance to route traffic for the 2 datacenters? 
