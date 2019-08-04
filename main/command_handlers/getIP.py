import subprocess

def getIP(worker):
    """
    Will send server's local IP adress
    """
    output = subprocess.getoutput("hostname -I")
    worker.answer_to_the_message(
        f"Output: {output}"
    )
