"""
This is the test dispatcher.

It will dispatch tests against any registered test runners when the repo
observer sends it a 'dispatch' message with the commit ID to be used. It
will store results when the test runners have completed running the tests and
send back the results in a 'results' messagee

It can register as many test runners as you like. To register a test runner,
be sure the dispatcher is started, then start the test runner.
"""
import click
import os
import re
import socket
import SocketServer
import time
import threading

import helpers


# Shared dispatcher code
def dispatch_tests(server, commit_id):
    # NOTE: usually we don't run this forever
    while True:
        print("trying to dispatch to runners")
        for runner in server.runners:
            response = helpers.communicate(runner["host"],
                                           int(runner["port"]),
                                           "runtest:%s" % commit_id)
            if response == "OK":
                print("adding id %s" % commit_id)
                server.dispatched_commits[commit_id] = runner
                if commit_id in server.pending_commits:
                    server.pending_commits.remove(commit_id)
                return
        time.sleep(2)


class ThreadingTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    runners = [] # Keeps track of test runner pool
    dead = False # Indicate to other threads that we are no longer running
    dispatched_commits = {} # Keeps track of commits we dispatched
    pending_commits = [] # Keeps track of commits we have yet to dispatch


class DispatcherHandler(SocketServer.BaseRequestHandler):
    """
    The RequestHandler class for our dispatcher.
    This will dispatch test runners against the incoming commit
    and handle their requests and test results
    """

    command_re = re.compile(r"(\w+)(:.+)*")
    BUF_SIZE = 1024

    ## command handlers
    def status_handler(self, command, message):
        print("in status")
        self.request.sendall("OK")

    def register_handler(self, command, message):
        # Add this test runner to our pool
        print("register")
        host, port = message.split(':')
        runner = {"host": host, "port":port}
        self.server.runners.append(runner)
        self.request.sendall("OK")

    def dispatcher_handler(self, command, message):
        print("going to dispatch")
        commit_id = message
        if not self.server.runners:
            self.request.sendall("No runners are registered")
        else:
            # The coordinator can trust us to dispatch the test
            self.request.sendall("OK")
            dispatch_tests(self.server, commit_id)

    def results_handler(self, command, message):
        print("got test results")
        results = message.split(":")
        commit_id = results[0]
        length_msg = int(results[1])
        # 3 is the number of ":" in the sent command
        remaining_buffer = self.BUF_SIZE - (len(command) + len(commit_id) + len(results[1]) + 3)
        if length_msg > remaining_buffer:
            self.data += self.request.recv(length_msg - remaining_buffer).strip()
        del self.server.dispatched_commits[commit_id]
        if not os.path.exists("test_results"):
            os.makedirs("test_results")
        with open("test_results/%s" % commit_id, "w") as f:
            data = self.data.split(":")[3:]
            data = "\n".join(data)
            f.write(data)
        self.request.sendall("OK")

    def handle(self):
        commands = {
                "status": self.status_handler,
                "register": self.register_handler,
                "dispatch": self.dispatcher_handler,
                "results": self.results_handler
                }

        # self.request is the TCP socket connected to the client
        self.data = self.request.recv(self.BUF_SIZE).strip()

        # parse the command header
        command_groups = self.command_re.match(self.data)
        if not command_groups:
            self.request.sendall("Invalid command")
            return
        command = command_groups.group(1)

        if command not in commands.keys():
            self.request.sendall("Invalid Command")
            return

        message = command_groups.group(2)[1:]
        commands[command](command, message)


# a thread to check the runner pool
def runner_checker(server):
    def manage_commit_lists(runner):
        for commit, assigned_runner in server.dispatched_commits.iteritems():
            if assigned_runner == runner:
                del server.dispatched_commits[commit]
                server.pending_commits.append(commit)
                break
        server.runners.remove(runner)

    while not server.dead:
        time.sleep(1)
        for runner in server.runners:
            try:
                response = helpers.communicate(runner["host"],
                                               int(runner["port"]),
                                               "ping")
                if response != "pong":
                    print("removing runner %s" % runner)
                    manage_commit_lists(runner)
            except socket.error as e:
                manage_commit_lists(runner)

# this will kick off tests that failed
def redistribute(server):
    while not server.dead:
        for commit in server.pending_commits:
            print("running redistribute")
            print(server.pending_commits)
            dispatch_tests(server, commit)
            time.sleep(5)


@click.command()
@click.option("--host",
        default="localhost",
        help="dispatcher's host, by default it uses localhost"
        )
@click.option("--port",
        default="8888",
        help="dispatcher's port, by default it uses 8888"
        )
def serve(host, port):
    # Create the server
    server = ThreadingTCPServer((host, int(port)), DispatcherHandler)
    print('serving on %s:%s' % (host, int(port)))

    runner_heartbeat = threading.Thread(target=runner_checker, args=(server,))
    redistributor = threading.Thread(target=redistribute, args=(server,))
    try:
        runner_heartbeat.start()
        redistributor.start()
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl+C or Cmd+C
        server.serve_forever()
    except (KeyboardInterrupt, Exception):
        # if any exception occurs, kill the thread
        server.dead = True
        runner_heartbeat.join()
        redistributor.join()


if __name__ == "__main__":
    serve()
