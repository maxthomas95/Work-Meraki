import os
import time
import meraki
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient

# ========================================
# Load secrets from .env
# ========================================
env_path = os.path.join(os.path.dirname(__file__), '../../.env')
print(f"Loading .env file from: {env_path}")
load_dotenv(dotenv_path=env_path)

organization_id = os.getenv('ORGANIZATION_ID')
tenant_id = os.getenv('AZURE_TENANT_ID')
client_id = os.getenv('AZURE_CLIENT_ID')
client_secret = os.getenv('AZURE_CLIENT_SECRET')
key_vault_name = os.getenv('AZURE_KEY_VAULT')
meraki_secret_name = os.getenv('MERAKI_SECRET_NAME')

# ========================================
# Authenticate to Azure Key Vault
# ========================================
kv_uri = f"https://{key_vault_name}.vault.azure.net"
credential = ClientSecretCredential(tenant_id, client_id, client_secret)
client = SecretClient(vault_url=kv_uri, credential=credential)
API_KEY = client.get_secret(meraki_secret_name).value

# ========================================
# Connect to Meraki Dashboard API
# ========================================
dashboard = meraki.DashboardAPI(API_KEY, suppress_logging=True)

# ========================================
# Configuration
# ========================================
network_id = ""  # TODO: Set target network ID
wait_time = 30   # TODO: Adjust wait time if needed

# ========================================
# Main Execution
# ========================================
if __name__ == '__main__':
    try:
        if not network_id:
            raise ValueError("Network ID must be set")

        # ========================================
        # Disable Network Services
        # ========================================
        print("\nDisabling network services...")
        vlans = dashboard.appliance.getNetworkApplianceVlans(network_id)
        
        for vlan in vlans:
            vlan_id = vlan['id']
            dashboard.appliance.updateNetworkApplianceVlan(
                network_id, vlan_id,
                dhcpHandling='Do not respond to DHCP requests'
            )
            print(f"Disabled DHCP for VLAN {vlan_id}")

        dashboard.appliance.updateNetworkApplianceVpnSiteToSiteVpn(
            network_id, 'none'
        )
        print("Disabled VPN connectivity")
        
        # ========================================
        # Wait Period
        # ========================================
        print(f"\nWaiting {wait_time} seconds...")
        time.sleep(wait_time)
        
        # ========================================
        # Restore Network Services
        # ========================================
        print("\nRestoring network services...")
        dashboard.appliance.updateNetworkApplianceVpnSiteToSiteVpn(
            network_id, 'spoke',
            hubs=[
                {'hubId': 'N_xxxx', 'useDefaultRoute': True},  # TODO: Update hub IDs
                {'hubId': 'N_xxxx', 'useDefaultRoute': True}   # TODO: Update hub IDs
            ]
        )
        print("Restored VPN connectivity")

        for vlan in vlans:
            vlan_id = vlan['id']
            dashboard.appliance.updateNetworkApplianceVlan(
                network_id, vlan_id,
                dhcpHandling='Relay DHCP to another server',
                dhcpRelayServerIps=['1.1.1.1', '8.8.8.8']  # TODO: Update DHCP relay IPs
            )
            print(f"Restored DHCP for VLAN {vlan_id}")

        print("\nNetwork services successfully restored")
        
    except Exception as e:
        print(f"[ERROR] Script execution failed: {e}")
        raise
