import paramiko
import getpass
from scp import SCPClient
from pathlib import Path
from modules.preprocess import preprocess_edf
# from modules.scp_uploader import scp_to_device


# REPLACE WITH REAL PYNQ PATH
# WILL ALSO NEED TO UPDATE HOST (ethernet?) TO SSH INTO PYNQ
# WILL ALSO NEED TO ssh-copy-id <username>@<pynq_ip> (verify by ssh, if no password prompt then good)
FAKE_PYNQ_DIR = str(
    Path.home().expanduser().resolve() / "fake_pynq" / "eeg_data"
)

# bin_path = "./test_data/processed_sleep.bin"



def preprocess_and_send(edf_path):
    print("SCP target:", FAKE_PYNQ_DIR)

    edf_path = Path(edf_path) # need this for .stem
    bin_path = (
        Path("./test_data") /
        f"{edf_path.stem}_processed.bin"
    )

    processed_path = preprocess_edf(edf_path, bin_path)

    scp_to_device(
        local_path=processed_path,
        remote_path=FAKE_PYNQ_DIR,
        host="127.0.0.1"
    )



def scp_to_device(local_path, remote_path, host):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # will need to change username= to <pynq_username> instead of getpass
    ssh.connect(hostname=host, username=getpass.getuser(), allow_agent=True, look_for_keys=True)

    with SCPClient(ssh.get_transport()) as scp:
        scp.put(local_path, remote_path)

    ssh.close()