# Copyright (c) 2023 Shvora Nikita, Livitsky Andrey
# This app, Ratsky Walnut, is licensed under the GNU General Public License version 3.0 (GPL 3.0).
# All source code, design, and other intellectual property rights of Ratsky Walnut, including but not limited to text, graphics, logos, images, and software, are the property of the Ratsky community and are protected by international copyright laws.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this app and associated documentation files (the "App"), to deal in the App without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the App, and to permit persons to whom the App is furnished to do so, subject to the following conditions:
#  1 The above copyright notice and this permission notice shall be included in all copies or substantial portions of the App.
#  2 Any distribution of the App or derivative works must include a copy of the GPL 3.0 license.
#  3 The App is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the App or the use or other dealings in the App.
# For more information on the GPL 3.0 license, please visit https://www.gnu.org/licenses/gpl-3.0.en.html.
import pika
import os
import paramiko
from loguru import logger


def get_queue_len(rabbitmq_url, rabbitmq_queue_name):
    connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
    channel = connection.channel()
    queue = channel.queue_declare(queue=rabbitmq_queue_name)
    message_count = queue.method.message_count
    return message_count

def ssh_copy_file(source, destination, ssh_user, ssh_password, ssh_host, ssh_port=22):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ssh_host, port=ssh_port, username=ssh_user, password=ssh_password)

        sftp = ssh.open_sftp()

        try:
            sftp.put(source, destination)
        except FileNotFoundError as e:
            logger.error(f"Remote directory does not exist: {os.path.dirname(destination)}")
            return {"status": False, "message": f"Remote directory does not exist: {os.path.dirname(destination)}"}
        except PermissionError as e:
            logger.error(f"No permission to write to remote directory: {os.path.dirname(destination)}")
            return {"status": False, "message": f"No permission to write to remote directory: {os.path.dirname(destination)}"}
        finally:
            sftp.close()

        ssh.close()
        logger.info(f"File copied successfully: {source} to {destination}")
        return {"status": True, "message": f"File copied successfully: {source} to {destination}"}

    except paramiko.ssh_exception.AuthenticationException as e:
        logger.error(f"Invalid SSH username or password")
        return {"status": False, "message": f"Invalid SSH username or password"}
    except Exception as e:
        logger.error(f"{e}")
        return {"status": False, "message": f"{e}"}



if __name__ == "__main__":
    print("No no no")
    # Example usage
    source = "/home/nshvora/testdfs.txt"
    destination = "/home/nshvora/text_rcync.txt"
    ssh_user = "nshvora"
    ssh_password = "JlKqwerT3228"
    ssh_host = "build-stand.ratsky.local"

    success = ssh_copy_file(source, destination, ssh_user, ssh_password, ssh_host)
    print("File copy successful:", success)