import argparse
from distutils.util import execute
from os.path import exists
from os import access, X_OK, mkdir, remove, getcwd, chdir
from subprocess import call
import sys

ALWAYS_YES = False
TF2_DIRECTORY = "tf2"
TF2_FULL_DIRECTORY = "tf2"
STEAMCMD_NICKNAME = "anonymous"

STEAMCMD = "steamcmd.exe"
STEAMCMD_LINIX = "./steam/steamcmd.sh"
STEAMCMD_URL_WIN32 = "http://media.steampowered.com/installer/steamcmd.zip"
STEAMCMD_URL_LINUX = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"

DOCKER_WINE = "docker-wine"
DOCKER_WINE_URL = "https://raw.githubusercontent.com/scottyhardy/docker-wine/master/docker-wine"

WGET_LOCATION = "/usr/bin/wget"
DOCKER_LOCATION = "/usr/bin/docker"
UNZIP_LOCATION = "/usr/bin/unzip"
BASH_LOCATION = "/bin/bash"

def steamcmd_check():
	return steamcmd_check_linux()

def steamcmd_check_linux():
	if not exists(STEAMCMD_LINIX):
		if not exists("steam"):
			mkdir("steam")
		chdir("steam")
		execute(f"{WGET_LOCATION} {STEAMCMD_URL_LINUX}")
		execute(f"tar -xf steamcmd_linux.tar.gz")
		execute("rm steamcmd_linux.tar.gz")
		chdir("..")
	execute(f"chmod +x {STEAMCMD_LINIX}")
	return True

def steamcmd_check_win32():
	if exists(STEAMCMD):
		execute(f"chmod 777 {STEAMCMD}")
		return True
	else:
		execute(f"{WGET_LOCATION} {STEAMCMD}")
		execute(f"{UNZIP_LOCATION} steamcmd.zip")
		if exists(STEAMCMD):
			if(exists("steamcmd.zip")):
				remove("steamcmd.zip")
			return True
		else:
			print("Failed download steamcmd, exit...")
			sys.exit(1)

def cmd_console():
	PWD = getcwd()
	docker_line = f"""{BASH_LOCATION} ./{DOCKER_WINE}
--volume={PWD}:/builder:rw
--env=\"USER_UID=1000\"
--env=\"USER_GID=1000\"
--env=\"USER_NAME=builder\"
wine cmd""".replace("\n", " ")
	print("Execute wine cmd")
	execute(docker_line)

def tf2_download():
	global STEAMCMD_NICKNAME
	if STEAMCMD_NICKNAME == "anonymous":
		STEAMCMD_NICKNAME = input("Enter your steam nickname: ")
	tf2_download_linux()

def tf2_download_linux():
	execute(f"""{BASH_LOCATION} {STEAMCMD_LINIX}
+@sSteamCmdForcePlatformType windows
+force_install_dir ../{TF2_DIRECTORY}
+login {STEAMCMD_NICKNAME}
+app_update 440
+quit""".replace("\n", " "))

def tf2_download_win32():
	PWD = getcwd()
	docker_line = f"""{BASH_LOCATION} ./{DOCKER_WINE}
--volume={PWD}:/builder:rw
--env=\"USER_UID=1000\"
--env=\"USER_GID=1000\"
--env=\"USER_NAME=builder\"
wine Z:\\builder\\{STEAMCMD}
+login {STEAMCMD_NICKNAME}
+force_install_dir Z:\\builder\\{TF2_DIRECTORY}
+app_update 440
validate
+quit""".replace("\n", " ")
	print("Execute docker")
	execute(docker_line)

def tf2_checks():
	if not exists(TF2_FULL_DIRECTORY):
		mkdir(TF2_FULL_DIRECTORY)

	for component in ["vbsp.exe", "vvis.exe", "vrad.exe"]:
		need_component = f"./{TF2_FULL_DIRECTORY}/bin/{component}"
		if not exists(need_component):
			print(f"Not found tf2 sdk on path: {need_component}")
			if wait_input("Install tf2?"):
				steamcmd_check()
				tf2_download()
				tf2_checks()
				if not exists(need_component):
					print("download tf2 failed!")
					sys.exit(1)
				print("tf2 sdk download successful from wine")
			else:
				print("Cannot continue, need tf2 sdk")
				sys.exit(1)
		else:
			print(f"Found: {need_component}")

def tf2_compiler_checks():
	return
	if not exists(TF2_FULL_DIRECTORY):
		print("Not found tf2 sdk")
		sys.exit(1)

	PWD = getcwd()
	for component in ["vbsp.exe", "vvis.exe", "vrad.exe"]:
		docker_line = f"""{BASH_LOCATION} ./{DOCKER_WINE}
--volume={PWD}/tf2:/tf2:rw
--env=\"USER_UID=1000\"
--env=\"USER_GID=1000\"
--env=\"USER_NAME=builder\"
wine Z:\\{TF2_DIRECTORY}\\bin\\{component} -game Z:\\{TF2_DIRECTORY}\\tf -help
""".replace("\n", " ")
		print(f"Execute {component} | {docker_line}")
		execute(docker_line)
		break

def tf2_compiler_build(vmf_file, threads = 16, vbsp = True, vvis = True, vrad = True):
	if not exists(vmf_file):
		print("build file not found")
		sys.exit(1)

	output = tf2_build_output(vmf_file)
	external_content = tf2_check_external_content()

	for component in ["vbsp.exe", "vvis.exe", "vrad.exe"]:
		docker_line = f"""{BASH_LOCATION} ./{DOCKER_WINE}
--volume={getcwd()}/tf2:/tf2:rw
{external_content}
{output}
""".replace("\n", " ")

		if vbsp and component == "vbsp.exe":
			docker_line += f"wine Z:\\{TF2_DIRECTORY}\\bin\\{component} -v -game Z:\\{TF2_DIRECTORY}\\tf Z:\\output\\{vmf_file}"
			print(f"Execute {component} | {docker_line}")
			execute(docker_line)
			continue

		if vvis and component == "vvis.exe":
			docker_line += f"wine Z:\\{TF2_DIRECTORY}\\bin\\{component} -v -threads {threads} -game Z:\\{TF2_DIRECTORY}\\tf Z:\\output\\{vmf_file}"
			print(f"Execute {component} | {docker_line}")
			execute(docker_line)
			continue

		if vrad and component == "vrad.exe":
			docker_line += f"wine Z:\\{TF2_DIRECTORY}\\bin\\{component} -v -both -final -threads {threads} -game Z:\\{TF2_DIRECTORY}\\tf Z:\\output\\{vmf_file}"
			print(f"Execute {component} | {docker_line}")
			execute(docker_line)
			continue

	print("Done! See output directory.")

def tf2_build_output(vmf_file):
	if not exists("output"):
		mkdir("output")
	from time import time
	output_directory = f"{getcwd()}/output/{vmf_file}.{int(time())}"
	extra_line = f"""--volume={output_directory}:/output:rw""".replace("\n", " ")
	execute(f"mkdir -p {output_directory}")
	execute(f"cp {vmf_file} {output_directory}/{vmf_file}")
	execute(f"chmod 777 -R {output_directory}")
	return extra_line

def tf2_check_external_content():
	PWD = getcwd()
	extra_line = ""
	if not exists("content"):
		mkdir("content")
		print("place in content directory external content if you use\nrun script again!!!")
		sys.exit(0)
	from glob import glob
	counter = 0
	for mount_point in glob("content/*"):
		print(f"Found external content: {mount_point}")
		extra_line += f"--volume={PWD}/{mount_point}:/{TF2_DIRECTORY}/tf/custom/{counter}:rw "
		counter += 1
	return extra_line

def execute(cmd):
	if not type(cmd) == list:
		cmd = cmd.split()
	return call(cmd)

def wait_input(text):
	if ALWAYS_YES:
		return True
	while True:
		try:
			result = input(text + " (yes/no)")
			if result.lower().find("yes") != -1:
				return True
			elif result.lower().find("no") != -1:
				return False
			else:
				continue
		except KeyboardInterrupt:
			print("Exit...")
			sys.exit(0)

def req_checks():
	if not exists(WGET_LOCATION):
		print(f"not found wget on this path: {WGET_LOCATION}")
		sys.exit(1)
	if not exists(DOCKER_LOCATION):
		print(f"not found docker on this path: {DOCKER_LOCATION}")
		sys.exit(1)

def wine_checks():
	if not exists(DOCKER_WINE):
		execute(f"{WGET_LOCATION} {DOCKER_WINE_URL}")

	if not access(DOCKER_WINE, X_OK):
		execute(f"chmod +x ./{DOCKER_WINE}")


if __name__ == "__main__":
	req_checks()
	wine_checks()
	parser = argparse.ArgumentParser()
	parser.add_argument("--cmd", action = "store_true")
	parser.add_argument("--download-tf2", type=str, help="Download TF2 files uses steamcmd, argument is your steam nickname")
	parser.add_argument("--build", type=str, help="full file name, example: zavod.vmf")
	args = parser.parse_args()

	if args.cmd:
		cmd_console()
		sys.exit(0)

	if args.download_tf2:
		STEAMCMD_NICKNAME = args.download_tf2
		steamcmd_check()
		tf2_download()
		sys.exit(0)

	if args.build:
		tf2_checks()
		tf2_compiler_checks()
		tf2_compiler_build(args.build)