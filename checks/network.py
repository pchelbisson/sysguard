import socket

def check_network(host, port):
    """Checking the availability of local ports."""
    check_network_dict = {
        "check_name": "check_network",
        "status": "UNKNOWN",
        "message": "",
        "data": {
            "host": host,
            "port": port
        }
    }
        
    try: # Create a socket object (AF_INET - IPv4, SOCK_STREAM - TCP)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            res = s.connect_ex((host, port))
            
            if res == 0:
                check_network_dict["status"] = "OK"
                check_network_dict["message"] = f"Port {port} on {host} is OPEN"
            else:
                check_network_dict["status"] = "WARNING"
                check_network_dict["message"] = f"Port {port} on {host} is CLOSED (Code: {res})"
                
    except Exception as e:
        check_network_dict["status"] = "ERROR"
        check_network_dict["message"] = f"Connection error: {e}"

    return check_network_dict