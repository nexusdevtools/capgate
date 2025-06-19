import subprocess

def run_cmd(cmd, capture_output=False):
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            return result.stdout
        else:
            subprocess.run(cmd, shell=True)
    except Exception as e:
        print(f"[!] Command failed: {cmd}\n{e}")
        return None
