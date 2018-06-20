"""
This is the repo observer.

It checks for new commits to the master repo, and will notify the dispatcher of
the latest commit ID, so the dispatcher can dispatch the tests against this
commit ID.
"""
import click
import os
import socket
import subprocess
import time

import helpers

@click.command()
@click.option("--dispatcher-server",
        default="localhost:8888",
        help="dispatcher host:port, by default it uses localhost:8888")
@click.option("--poll-interval",
        default=5,
        type=int,
        help="poll interval to check if the repository is updated")
@click.argument("repo", default="", nargs=1)
def poll(dispatcher_server, poll_interval, repo):
    dispatcher_host, dispatcher_port = dispatcher_server.split(":")
    while True:
        try:
            # call the bash script that will update the repo and check
            # for changes. If there's a change, it will drop a .commit_id file
            # with the latest commit in the current working directory
            subprocess.check_output(["./update_repo.sh", repo])
        except subprocess.CalledProcessError as e:
            raise Exception("Could not update and check repository. Reason: %s" % e.output)

        if os.path.isfile(".commit_id"):
            # great, we have a change! let's execute the tests
            # First, check the status of the dispatcher server to see
            # if we can send the tests
            try:
                response = helpers.communicate(dispatcher_host,
                                               int(dispatcher_port),
                                               "status:check")
            except socket.error as e:
                raise Exception("Could not communicate with dispatcher server: %s" % e)
            if response == "OK":
                # Dispatcher is present, let's send it a test
                commit = ""
                with open(".commit_id", "r") as f:
                    commit = f.readline()
                response = helpers.communicate(dispatcher_host,
                                               int(dispatcher_port),
                                               "dispatch:%s" % commit)
                if response != "OK":
                    raise Exception("Could not dispatch the test: %s" %
                    response)
                print("dispatched!")
            else:
                # Something wrong happened to the dispatcher
                raise Exception("Could not dispatch the test: %s" % response)
        time.sleep(poll_interval)


if __name__ == "__main__":
    poll()
