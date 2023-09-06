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

if __name__ == '__main__':
    branch = sys.argv[1]
    commit_message = sys.argv[2]
    user_name = sys.argv[3]
    user_password = sys.argv[4]

    logger.info(f"\033[1;36mCreating {branch}\033[0m")
    checkout_command = pexpect.spawn(f"git checkout -b {branch}")
    checkout_command.logfile_read = sys.stdout.buffer
    checkout_command.expect(f"Switched to a new branch '{branch}'")
    checkout_command.expect(pexpect.EOF)
    logger.info(f"\033[1;92m\U00002714 Successfully checked out {branch}\033[0m")

    logger.info("\033[1;36mAdding all changed and new files\033[0m")
    add_command = pexpect.spawn("git add --all")
    add_command.logfile_read = sys.stdout.buffer
    add_command.expect(pexpect.EOF)
    add_command.close()
    assert add_command.exitstatus == 0, "Failed to add files"
    logger.info("\033[1;92m\U00002714 Successfully added all files\033[0m")

    logger.info("\033[1;36mCommitting changes\033[0m")
    commit_command = pexpect.spawn(f"git commit -m '{commit_message}'")
    commit_command.logfile_read = sys.stdout.buffer
    commit_command.expect(pexpect.EOF)
    add_command.close()
    assert add_command.exitstatus == 0, "Failed to commit changes"
    logger.info(f"\033[1;92m\U00002714 Successfully committed all changes\033[0m")

    logger.info(f"\033[1;36mPushing {branch}\033[0m")
    push_command = pexpect.spawn(f"git push origin {branch}")
    push_command.logfile_read = sys.stdout.buffer
    send_authentication(push_command, user_name, user_password)
    push_command.expect(pexpect.EOF)
    logger.info(f"\033[1;92m\U00002714 Successfully pushed {branch}\033[0m")

