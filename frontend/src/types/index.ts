export interface Host {
  id: number;
  ip_address: string;
  ssh_port: number;
  ssh_user: string;
  rack_name: string;
  os_type: string | null;
  status: string;
  cpu_cores: number | null;
  ram_mb: number | null;
  disk_gb: number | null;
  gateway: string | null;
  subnet_mask: string | null;
  dns_servers: string | null;
  bridge_interface: string | null;
  hypervisor_installed: boolean | null;
  hypervisor_type: string | null;
  bridge_configured: boolean | null;
  created_at: string;
  updated_at: string;
}

export interface HostCreate {
  ip_address: string;
  ssh_port?: number;
  ssh_user?: string;
  ssh_key_path?: string;
  ssh_password?: string;
}

export interface HypervisorCheck {
  installed: boolean;
  hypervisor_type: string | null;
  version: string | null;
  install_commands: string[] | null;
}

export interface BridgeCheck {
  configured: boolean;
  bridge_name: string | null;
  output: string | null;
  setup_commands: string[] | null;
}

export interface VM {
  id: number;
  name: string;
  host_id: number;
  ip_address: string;
  status: string;
  cpu_cores: number;
  ram_mb: number;
  disk_gb: number;
  os_image: string;
  ssh_key_id: number | null;
  rack_sequence: number;
  created_at: string;
  updated_at: string;
  host_ip?: string;
  rack_name?: string;
  cluster_name?: string;
}

export interface VMCreate {
  host_id?: number;
  cpu_cores?: number;
  ram_mb?: number;
  disk_gb?: number;
  os_image?: string;
  ssh_key_id?: number;
}

export interface VMsByRack {
  rack_name: string;
  host_ip: string;
  vms: VM[];
}

export interface VMReadiness {
  hypervisor_running: boolean;
  ip_reachable: boolean;
  ssh_port_open: boolean;
  ssh_auth_ok: boolean;
  cloud_init_status: string | null;
}

export interface SSHKey {
  id: number;
  name: string;
  public_key: string;
  private_key_path: string;
  fingerprint: string;
  created_at: string;
}

export interface Cluster {
  id: number;
  name: string;
  status: string;
  k3s_version: string;
  control_plane_count: number;
  worker_count: number;
  created_at: string;
  updated_at: string;
  nodes: ClusterNode[];
}

export interface ClusterCreate {
  name: string;
  control_plane_count?: number;
  worker_count?: number;
  cpu_cores?: number;
  ram_mb?: number;
  disk_gb?: number;
  os_image?: string;
  k3s_version?: string;
  ssh_key_id: number;
  host_ids?: number[];
}

export interface ClusterPreview {
  distribution: Record<string, Record<string, number>>;
  total_vms: number;
  total_cpu: number;
  total_ram_mb: number;
  total_disk_gb: number;
}

export interface ClusterNode {
  id: number;
  cluster_id: number;
  vm_id: number;
  role: string;
  status: string;
  vm_name?: string;
  vm_ip?: string;
  host_ip?: string;
  rack_name?: string;
  created_at: string;
}

export interface ClusterStatus {
  status: string;
  message: string;
  progress: number | null;
}

export interface IPAllocation {
  id: number;
  ip_address: string;
  vm_id: number | null;
  vm_name?: string;
  is_reserved: boolean;
  notes: string | null;
  created_at: string;
}

export interface IPAvailable {
  available_ips: string[];
  total_available: number;
  total_range: number;
}

export interface IPConfig {
  range_start: string;
  range_end: string;
  subnet_mask: string;
  gateway: string;
  dns: string[];
}

export interface WGStatus {
  interface: string;
  public_key: string;
  listen_port: number;
  address: string;
  is_up: boolean;
  peers: WGPeer[];
}

export interface WGPeer {
  datacenter_code: string;
  public_key: string;
  endpoint: string;
  allowed_ips: string;
  comment?: string;
  latest_handshake?: string;
  transfer_rx?: string;
  transfer_tx?: string;
}

export interface WGPeerCreate {
  datacenter_code: string;
  public_key: string;
  endpoint: string;
  allowed_ips: string;
  comment?: string;
}
