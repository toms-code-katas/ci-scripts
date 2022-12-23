import logging
import sys
import pexpect

logging.basicConfig(
    level=logging.DEBUG,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def send_authentication(expect_command, user_name, user_password):
    expect_command.expect("Username for ")
    expect_command.sendline(user_name)
    expect_command.expect("Password for ")
    expect_command.sendline(user_password)


def clone_repo(repo_url, repo_name, user_name, user_password):
    logger.info(f"\033[1;36mCloning {repo_url} into {repo_name} as {user_name}\033[0m")
    clone_command = pexpect.spawn(f"git clone {repo_url} {repo_name}")
    clone_command.logfile_read = sys.stdout.buffer
    send_authentication(clone_command, user_name, user_password)
    clone_command.expect(pexpect.EOF)
    logger.info(f"\033[1;92m\U00002714 Successfully cloned {repo_name}\033[0m")


def init_submodules(repo_name, user_name, user_password):
    logger.info(f"\033[1;36mInitializing submodules in {repo_name}\033[0m")
    init_command = pexpect.spawn(f"git submodule update --init --recursive", cwd=repo_name)
    init_command.logfile_read = sys.stdout.buffer
    send_authentication(init_command, user_name, user_password)
    init_command.expect(pexpect.EOF)
    logger.info(f"\033[1;92m\U00002714 Successfully initialized submodules\033[0m")


def set_user(user_name, user_email, repo_name):
    logger.info(f"\033[1;36mSetting user to {user_name} and email to {user_email}\033[0m")
    set_user_command = pexpect.spawn(f"git config user.name {user_name}", cwd=repo_name)
    set_user_command.logfile_read = sys.stdout.buffer
    set_user_command.expect(pexpect.EOF)
    set_email_command = pexpect.spawn(f"git config user.email {user_email}", cwd=repo_name)
    set_email_command.logfile_read = sys.stdout.buffer
    set_email_command.expect(pexpect.EOF)
    logger.info(f"\033[1;92m\U00002714 Successfully set user and email\033[0m")


if __name__ == '__main__':
    repo_url = sys.argv[1]
    repo_name = repo_url.split('/')[-1].split('.')[0]

    user_name = sys.argv[2]
    user_password = sys.argv[3]

    clone_repo(repo_url, repo_name, user_name, user_password)
    init_submodules(repo_name, user_name, user_password)
    set_user(user_name, user_name, repo_name)