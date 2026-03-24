import paramiko
import getpass
from scp import SCPClient
from pathlib import Path
from modules.preprocess import preprocess_edf


# REPLACE WITH REAL PYNQ PATH
# WILL ALSO NEED TO UPDATE HOST (ethernet?) TO SSH INTO PYNQ
# WILL ALSO NEED TO ssh-copy-id <username>@<pynq_ip> (verify by ssh, if no password prompt then good)
FAKE_PYNQ_DIR = str(
    # Path.home().expanduser().resolve() / "fake_pynq" / "eeg_data"  # CHANGE
    "/home/xilinx/uploads"
)

# bin_path = "./test_data/processed_sleep.bin"

# Global SSH connection (established at dashboard startup)
_ssh_connection = None
_ssh_host = None
_ssh_username = None


class SSHConnectionManager:
    """Manages a persistent SSH connection to the PYNQ board"""
    
    def __init__(self, host: str, username: str = None):
        """
        Initialize SSH connection manager.
        
        Args:
            host: PYNQ board hostname/IP address
            username: SSH username (defaults to current system user)
        """
        self.host = host
        self.username = username or getpass.getuser()
        self.ssh = None
        self._is_connected = False
    
    def connect(self) -> bool:
        """
        Establish SSH connection to PYNQ board.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # self.ssh.connect(
            #     hostname=self.host,
            #     username=self.username,
            #     allow_agent=True,
            #     look_for_keys=True,
            #     timeout=10
            # )
            self.ssh.connect(  # CHANGE
                hostname=self.host,
                username=self.username,
                password="xilinx",
                allow_agent=True,
                look_for_keys=False,
                timeout=10
            )
            self._is_connected = True
            print(f"SSH connection established to {self.host} as {self.username}")
            return True
        except Exception as e:
            print(f"Failed to establish SSH connection: {e}")
            self._is_connected = False
            return False
    
    def is_connected(self) -> bool:
        """Check if SSH connection is active"""
        return self._is_connected and self.ssh is not None
    
    def disconnect(self):
        """Close SSH connection"""
        if self.ssh:
            try:
                self.ssh.close()
                self._is_connected = False
                print(f"SSH connection to {self.host} closed")
            except Exception as e:
                print(f"Error closing SSH connection: {e}")
    
    def execute_command(self, command: str, stdin_data: str = None) -> tuple[str, str, int]:
        """
        Execute a command on the remote PYNQ board.
        
        Args:
            command: Shell command to execute
            stdin_data: Optional data to send to stdin (e.g., password for sudo)
        
        Returns:
            Tuple of (stdout, stderr, return_code)
        """
        if not self.is_connected():
            raise RuntimeError("SSH connection not established")
        
        try:
            stdin, stdout, stderr = self.ssh.exec_command(command)
            if stdin_data:
                stdin.write(stdin_data + '\n')
                stdin.flush()
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')
            return_code = stdout.channel.recv_exit_status()
            return stdout_data, stderr_data, return_code
        except Exception as e:
            print(f"Error executing command '{command}': {e}")
            raise


def setup_ssh_connection(host: str, username: str = None) -> SSHConnectionManager:
    """
    Set up global SSH connection to PYNQ board.
    
    Args:
        host: PYNQ board hostname/IP address
        username: SSH username (defaults to current system user)
    
    Returns:
        SSHConnectionManager instance
    
    Raises:
        RuntimeError if connection fails
    """
    global _ssh_connection, _ssh_host, _ssh_username
    
    # Close any existing connection
    if _ssh_connection:
        _ssh_connection.disconnect()
    
    # Create new connection
    _ssh_connection = SSHConnectionManager(host, username)
    if not _ssh_connection.connect():
        raise RuntimeError(f"Could not establish SSH connection to {host}")
    
    _ssh_host = host
    _ssh_username = username or getpass.getuser()
    
    return _ssh_connection


def get_ssh_connection() -> SSHConnectionManager:
    """Get the global SSH connection instance"""
    global _ssh_connection
    if _ssh_connection is None:
        raise RuntimeError("SSH connection not initialized. Call setup_ssh_connection first.")
    return _ssh_connection


def preprocess_and_send(edf_path):
    print("SCP target:", FAKE_PYNQ_DIR)

    edf_path = Path(edf_path) # need this for .stem
    npy_path = (
        Path("./test_data") /
        f"{edf_path.stem}_processed.npy"
    )

    # if .edf file
    if edf_path.suffix == ".edf":
        # process edf to npy
        processed_path = preprocess_edf(edf_path, npy_path)
    elif edf_path.suffix == ".npy":
        # send npy file in npz path
        processed_path = Path(edf_path).with_name(
            Path(edf_path).stem.replace("-epochs", "") + ".npz"
        )
    else:
        raise ValueError("Unsupported file type")

    scp_to_device(
        local_path=processed_path,
        remote_path=FAKE_PYNQ_DIR,
        # host="127.0.0.1"
        host="192.168.137.28"  # CHANGE
    )



def scp_to_device(local_path: str, remote_path: str, host: str):
    """
    Transfer a file to PYNQ device using SCP over persistent SSH connection.
    
    Args:
        local_path: Path to local file
        remote_path: Path on remote PYNQ board
        host: PYNQ board hostname/IP (used to get/setup SSH connection)
    """
    # Get or setup SSH connection
    if _ssh_connection is None or _ssh_connection.host != host:
        setup_ssh_connection(host)
    
    ssh_conn = get_ssh_connection()
    
    if not ssh_conn.is_connected():
        raise RuntimeError("SSH connection not active")
    
    try:
        with SCPClient(ssh_conn.ssh.get_transport()) as scp:
            scp.put(local_path, remote_path)
        print(f"Successfully transferred {local_path} to {host}:{remote_path}")
    except Exception as e:
        print(f"SCP transfer failed: {e}")
        raise



def signal_fpga_process_file(filename: str) -> tuple[str, str, int]:
    """
    Signal the FPGA to start processing a file using an SSH command.
    
    Args:
        filename: Name of the file to process on the FPGA
    
    Returns:
        Tuple of (stdout, stderr, return_code) from remote command execution
    """
    ssh_conn = get_ssh_connection()
    
    if not ssh_conn.is_connected():
        raise RuntimeError("SSH connection not active")
    
    # Create command to run processing script with filename argument
    command = f"sudo -S bash -lc 'source /etc/profile.d/pynq_venv.sh && source /etc/profile.d/xrt_setup.sh && /usr/local/share/pynq-venv/bin/python3 /home/xilinx/timed_board.py --input-npz /home/xilinx/uploads/{filename} --bitfile /home/xilinx/design_2_wrapper.bit --model /home/xilinx/TESTtinysleepnetdwt-nonormalized-2e-4.tflite --host 192.168.137.1 --port 9999 --seconds-per-step 1.0'"

    print(f"Signaling FPGA to process file: {filename}")
    print(f"Executing command on PYNQ board...")
    
    try:
        # Pass "xilinx" password via stdin for sudo -S
        stdout, stderr, return_code = ssh_conn.execute_command(command, stdin_data="xilinx")
        
        print(f"FPGA Command execution completed with return_code={return_code}")
        
        if return_code == 0:
            print(f"FPGA processing started successfully")
        else:
            print(f"FPGA processing command failed with code {return_code}")
        
        if stdout:
            print(f"FPGA stdout: {stdout}")
        if stderr:
            print(f"FPGA stderr: {stderr}")
        
        return stdout, stderr, return_code
    except Exception as e:
        print(f"Failed to signal FPGA: {e}")
        raise


def stop_fpga_processing() -> None:
    """
    Signal the FPGA to stop any currently running processing script.
    Uses pkill to terminate the timed_board.py process.
    """
    ssh_conn = get_ssh_connection()
    
    if not ssh_conn.is_connected():
        print("SSH connection not active, can't stop FPGA")
        return
    
    # Create command to kill the processing script
    command = "pkill -f timed_board.py"
    
    print(f"Signaling FPGA to stop processing...")
    
    try:
        stdout, stderr, return_code = ssh_conn.execute_command(command)
        
        if return_code == 0:
            print(f"FPGA processing stopped successfully")
        else:
            # pkill returns 1 if no process was found, which is fine
            if "no process" in stderr.lower() or return_code == 1:
                print(f"No running process to stop")
            else:
                print(f"Stop command returned code {return_code}")

        if stdout:
            print(f"stdout: {stdout}")
        if stderr and "no process" not in stderr.lower():
            print(f"stderr: {stderr}")

    except Exception as e:
        print(f"Failed to stop FPGA: {e}")
