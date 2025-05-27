#!/usr/bin/python3
import socket
import json
import argparse
import glob
import sys
try:
    from tabulate import tabulate
except ModuleNotFoundError:
    print("Missing dependency. Please run \napt install python3-tabulate")
    raise
    sys.exit(1)
from datetime import datetime, timedelta
from pathlib import Path


def get_fastd_status(socket_path):
    try:
        # Verbindung zum fastd-Socket herstellen
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_path)

        # Daten vom Socket empfangen
        data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk

        # Schließen Sie die Socket-Verbindung
        sock.close()

        return data.decode('utf-8')
    except Exception as e:
        print(f"Fehler beim Lesen des fastd-Sockets '{socket_path}': {e}")
        raise
        return None


def calculate_bandwidth(bytes_transferred, established_time_ms):
    # Zeit in Sekunden umrechnen
    established_time_sec = established_time_ms / 1000

    # Bandbreite in kbit/s berechnen
    bandwidth_kbps = (bytes_transferred * 8) / (established_time_sec * 1000)

    return bandwidth_kbps


def format_duration(established_time_ms):
    # Zeit in Sekunden umrechnen
    established_time_sec = established_time_ms / 1000

    # Dauer in Tagen umrechnen
    duration = timedelta(seconds=established_time_sec)
    days = duration.days

    return f"{days}d"


def find_top_peers_with_bandwidth(socket_paths, top_n=10):
    all_peers = []

    for socket_path in socket_paths:
        status_data = get_fastd_status(socket_path)

        if status_data:
            try:
                # JSON-Daten analysieren
                status_json = json.loads(status_data)

                # Extrahiere die Peer-Informationen
                peers = status_json.get('peers', {})

                for peer_key, peer_info in peers.items():
                    try:
                        if peer_info['connection'] is not None:
                            bytes_transferred = peer_info['connection']['statistics']['tx']['bytes']
                            established_time_ms = peer_info['connection']['established']

                            bandwidth_kbps = calculate_bandwidth(
                                bytes_transferred, established_time_ms)
                            duration_formatted = format_duration(
                                established_time_ms)

                            all_peers.append({
                                'peer_key': peer_key,
                                'socket_path': socket_path,
                                'bandwidth_kbps': bandwidth_kbps,
                                'duration_formatted': duration_formatted
                            })
                    except Exception as e:
                        print(30*"=")
                        print(
                            f"Fehler beim Analysieren der Daten für peer '{peer_key}': {e}")
                        print(peer_key)
                        print(peer_info)
                        print(30*"=")
            except Exception as e:
                print(
                    f"Fehler beim Analysieren der fastd-Statusdaten für Socket '{socket_path}': {e}")

    # Sortiere die Peers nach der Bandbreite in kbit/s in absteigender Reihenfolge
    sorted_peers = sorted(
        all_peers, key=lambda x: x['bandwidth_kbps'], reverse=True)

    # Begrenze die Liste auf die Top-N Peers
    top_peers = sorted_peers[:top_n]

    return top_peers


def display_table_with_graph(top_peers):
    try:
        headers = ["Peer Key", "Socket Path", "Bandwidth (kbit/s)", "Duration"]
        rows = []

        for peer_info in top_peers:
            peer_key = peer_info['peer_key']
            socket_path = peer_info['socket_path']
            bandwidth_kbps = peer_info['bandwidth_kbps']
            duration_formatted = peer_info['duration_formatted']

            rows.append(
                [peer_key, socket_path, f"{bandwidth_kbps:.2f}", duration_formatted])

        # Tabellarische Ausgabe
        table = tabulate(rows, headers=headers, tablefmt='grid')

        print(table)
    except Exception as e:
        print(f"Fehler beim Anzeigen der Tabelle mit Balkengrafik: {e}")


def touch(top_peers):
    for t in top_peers:
        k = t["peer_key"]
        Path("/var/lib/ffs/blocked_keys").mkdir(parents=True, exist_ok=True)
        Path(f"/var/lib/ffs/blocked_keys/{k}").touch()


def main():
    parser = argparse.ArgumentParser(
        description='Analysiere den fastd-Status und zeige die Top-N Peers mit der höchsten Bandbreite über alle Sockets an.')
    parser.add_argument('--top', type=int, default=10,
                        help='Anzahl der Top-Peers, die angezeigt werden sollen')
    parser.add_argument('--touch', action="store_true",
                        help='touch files with name equal key to remove tunnels')

    args = parser.parse_args()
    top_n = args.top

    # Finde alle Sockets in /var/run/, die mit "fastd-vp" beginnen
    socket_paths = glob.glob('/var/run/fastd-vp*.sock') + glob.glob('/var/run/fastd/fastd-vp*.sock')

    if not socket_paths:
        print("Keine passenden Sockets gefunden.")
        return

    top_peers = find_top_peers_with_bandwidth(socket_paths, top_n)

    if top_peers:
        display_table_with_graph(top_peers)
        if args.touch:
            touch(top_peers)
    else:
        print("Keine Peer-Informationen gefunden.")


if __name__ == "__main__":
    main()
