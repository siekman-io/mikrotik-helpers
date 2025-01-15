import paramiko
import re
import json

def fetch_brute_force_data(server, port, username, key_path, file_path):
    """
    Haal brute force gegevens op van de server via SSH.

    :param server: Serveradres
    :param port: Poortnummer voor SSH
    :param username: Gebruikersnaam om in te loggen
    :param key_path: Pad naar de SSH-sleutel
    :param file_path: Pad naar het brute_ip.data bestand
    :return: Lijst van IP-adressen met meer dan 100 loginpogingen
    """
    try:
        # SSH-client configureren
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server, port=port, username=username, key_filename=key_path)

        # Elevate naar root
        stdin, stdout, stderr = ssh.exec_command("sudo cat " + file_path)
        stdin.write("your_password\n")  # Verander dit in je root-wachtwoord of gebruik een sleutelpaar
        stdin.flush()

        # Lees de inhoud van het bestand
        file_content = stdout.read().decode('utf-8')

        ssh.close()

        # Parse de inhoud van het bestand
        ip_attempts = {}
        for line in file_content.splitlines():
            match = re.match(r"^(\d+\.\d+\.\d+\.\d+)=.*wordpress2=(\d+)", line)
            if match:
                ip = match.group(1)
                attempts = int(match.group(2))
                if attempts > 100:
                    ip_attempts[ip] = attempts

        return ip_attempts

    except Exception as e:
        print(f"Fout bij het ophalen van gegevens: {e}")
        return {}

def save_to_file(data, file_path):
    """
    Sla data op in een bestand.

    :param data: De data om op te slaan
    :param file_path: Pad naar het bestand
    """
    try:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
        print(f"Data succesvol opgeslagen in {file_path}")
    except Exception as e:
        print(f"Fout bij het opslaan van data: {e}")

def generate_mikrotik_list(ip_attempts, list_name):
    """
    Genereer een adreslijst voor Mikrotik.

    :param ip_attempts: Dictionary met IP-adressen en loginpogingen
    :param list_name: Naam van de adreslijst in Mikrotik
    :return: Mikrotik configuratie regels
    """
    mikrotik_rules = [
        f"/ip firewall address-list remove [find where comment=\"brute_force\"]"
    ]
    for ip in ip_attempts.keys():
        mikrotik_rules.append(f"/ip firewall address-list add list={list_name} address={ip} comment=brute_force")
    return mikrotik_rules

if __name__ == "__main__":
    # Configuratie voor meerdere servers
    servers = [
        {"host": "da1.siekman.io", "port": 20222, "username": "sysops", "key_path": "/home/siekman/.ssh/js", "file_path": "/usr/local/directadmin/data/admin/brute_ip.data"},
        {"host": "da2.siekman.io", "port": 20222, "username": "sysops", "key_path": "/home/siekman/.ssh/js", "file_path": "/usr/local/directadmin/data/admin/brute_ip.data"}
    ]

    all_ip_attempts = {}

    for server in servers:
        print(f"Haal gegevens op van de brute force monitor op {server['host']}...")
        ip_attempts = fetch_brute_force_data(server['host'], server['port'], server['username'], server['key_path'], server['file_path'])

        if ip_attempts:
            print(f"IP-adressen met meer dan 100 loginpogingen op {server['host']}:")
            for ip, attempts in ip_attempts.items():
                print(f"IP: {ip}, Pogingen: {attempts}")
                all_ip_attempts[ip] = attempts

    if all_ip_attempts:
        save_to_file(all_ip_attempts, "bruteforce.json")

        # Genereer Mikrotik adreslijst regels
        mikrotik_rules = generate_mikrotik_list(all_ip_attempts, "BRUTE_FORCE")
        mikrotik_file = "bruteforce.rsc"
        try:
            with open(mikrotik_file, 'w') as file:
                file.write("\n".join(mikrotik_rules))
            print(f"Mikrotik configuratie opgeslagen in {mikrotik_file}")
        except Exception as e:
            print(f"Fout bij het opslaan van Mikrotik configuratie: {e}")
    else:
        print("Geen IP-adressen gevonden met meer dan 100 loginpogingen.")

